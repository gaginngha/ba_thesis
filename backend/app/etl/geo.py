"""
ETL pipeline for geospatial data.

Downloads municipality boundaries from swisstopo / BFS ThemaKart:
- swissBOUNDARIES3D municipality boundaries
- Generalized boundaries for web display
"""

import json
import zipfile
from pathlib import Path

import httpx
from loguru import logger
from sqlalchemy import create_engine, text

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# swisstopo generalized municipality boundaries (GeoJSON)
# ThemaKart boundaries — simplified for web use
GEO_DATASETS = {
    # BFS ThemaKart generalized municipality boundaries
    "municipalities_geojson": "https://dam-api.bfs.admin.ch/hub/api/dam/assets/32006092/master",
    # Alternative: opendata.swiss simplified boundaries
    "municipalities_topojson": "https://dam-api.bfs.admin.ch/hub/api/dam/assets/32006093/master",
}


async def download_boundaries(url: str, filename: str) -> Path:
    """Download boundary file."""
    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    filepath = raw_dir / filename

    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        logger.info(f"Downloading boundaries: {url}")
        response = await client.get(url)
        response.raise_for_status()
        filepath.write_bytes(response.content)

    logger.info(f"Downloaded {filepath} ({filepath.stat().st_size / 1024:.1f} KB)")

    # Handle zip files
    if filepath.suffix == ".zip":
        extract_dir = raw_dir / filepath.stem
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(filepath, "r") as z:
            z.extractall(extract_dir)
        logger.info(f"Extracted to {extract_dir}")
        return extract_dir

    return filepath


def parse_geojson_boundaries(filepath: Path) -> list[dict]:
    """
    Parse GeoJSON file containing municipality boundaries.
    Returns list of dicts with bfs_number and geometry WKT.
    """
    logger.info(f"Parsing GeoJSON boundaries from {filepath}")

    # Find the GeoJSON file
    geojson_path = filepath
    if filepath.is_dir():
        candidates = list(filepath.glob("**/*.geojson")) + list(filepath.glob("**/*.json"))
        if candidates:
            geojson_path = candidates[0]
        else:
            logger.error(f"No GeoJSON files found in {filepath}")
            return []

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    results = []

    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry")

        # BFS number can be in various property names
        bfs_number = None
        for key in ["GMDNR", "BFS_NR", "GMDE", "id", "GDENR", "bfs_nr", "gemeindenummer"]:
            if key in props:
                try:
                    bfs_number = int(props[key])
                    break
                except (ValueError, TypeError):
                    continue

        if bfs_number and geometry:
            # Convert geometry to GeoJSON string
            geom_json = json.dumps(geometry)
            results.append({
                "bfs_number": bfs_number,
                "name": props.get("GMDNAME", props.get("NAME", props.get("name", ""))),
                "geometry_geojson": geom_json,
            })

    logger.info(f"Parsed {len(results)} municipality boundaries")
    return results


def load_boundaries_to_db(boundaries: list[dict], db_url: str, source_srid: int = 2056):
    """
    Load municipality boundaries into PostGIS.

    Args:
        boundaries: List of dicts with bfs_number, geometry_geojson
        source_srid: Source coordinate system (2056 = Swiss LV95, 4326 = WGS84)
    """
    engine = create_engine(db_url)
    loaded = 0

    with engine.begin() as conn:
        for b in boundaries:
            try:
                # Use ST_GeomFromGeoJSON and transform to LV95 if needed
                if source_srid == 4326:
                    conn.execute(
                        text("""
                            UPDATE municipalities
                            SET geometry = ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 2056))
                            WHERE bfs_number = :bfs
                        """),
                        {"bfs": b["bfs_number"], "geom": b["geometry_geojson"]},
                    )
                else:
                    conn.execute(
                        text("""
                            UPDATE municipalities
                            SET geometry = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geom), :srid))
                            WHERE bfs_number = :bfs
                        """),
                        {"bfs": b["bfs_number"], "geom": b["geometry_geojson"], "srid": source_srid},
                    )
                loaded += 1
            except Exception as e:
                logger.warning(f"Failed to load boundary for BFS {b['bfs_number']}: {e}")

    logger.info(f"Loaded {loaded}/{len(boundaries)} municipality boundaries into PostGIS")


def generate_static_geojson(db_url: str, output_path: Path, simplify_tolerance: float = 50.0):
    """
    Generate a pre-simplified GeoJSON file for frontend use.
    This avoids the need for PostGIS queries on every map load.
    """
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text(f"""
            SELECT
                m.bfs_number,
                m.name,
                c.abbreviation as canton,
                m.population,
                ST_AsGeoJSON(
                    ST_Transform(
                        ST_Simplify(m.geometry, {simplify_tolerance}),
                        4326
                    )
                ) as geojson
            FROM municipalities m
            JOIN cantons c ON m.canton_id = c.id
            WHERE m.is_active = TRUE AND m.geometry IS NOT NULL
            ORDER BY m.bfs_number
        """))
        rows = result.all()

    features = []
    for row in rows:
        if row.geojson:
            features.append({
                "type": "Feature",
                "properties": {
                    "bfs": row.bfs_number,
                    "name": row.name,
                    "canton": row.canton,
                    "pop": row.population,
                },
                "geometry": json.loads(row.geojson),
            })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)

    logger.info(f"Generated static GeoJSON with {len(features)} features -> {output_path}")


async def run_geo_pipeline(db_url: str):
    """Main ETL pipeline for geospatial data."""
    logger.info("Starting geospatial data ETL pipeline")

    try:
        filepath = await download_boundaries(
            GEO_DATASETS["municipalities_geojson"],
            "bfs_municipality_boundaries.zip",
        )
        boundaries = parse_geojson_boundaries(filepath)

        if boundaries:
            # Detect SRID from data — BFS ThemaKart uses LV95 (2056) or WGS84 (4326)
            # Check if coordinates look like Swiss LV95 (x > 2'000'000) or WGS84 (lat/lon)
            sample = json.loads(boundaries[0]["geometry_geojson"])
            coords = sample.get("coordinates", [[[[0, 0]]]])
            # Flatten to get a sample coordinate
            flat = coords
            while isinstance(flat, list) and isinstance(flat[0], list):
                flat = flat[0]
            sample_x = flat[0] if isinstance(flat, list) and len(flat) >= 2 else 0

            source_srid = 2056 if sample_x > 100000 else 4326
            logger.info(f"Detected source SRID: {source_srid} (sample x: {sample_x})")

            load_boundaries_to_db(boundaries, db_url, source_srid=source_srid)

            # Generate static GeoJSON for frontend
            static_path = Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "municipalities.geojson"
            generate_static_geojson(db_url, static_path)

    except Exception as e:
        logger.error(f"Failed geospatial pipeline: {e}")

    logger.info("Geospatial ETL pipeline complete")
