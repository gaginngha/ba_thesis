"""
ETL pipeline for BFS (Federal Statistical Office) data.

Downloads municipality demographics, economic data, and master data from:
- BFS PXWeb API
- opendata.swiss
- BFS Gemeindeverzeichnis (municipality register)
"""

from pathlib import Path

import httpx
import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# BFS PXWeb API base URL
PXWEB_BASE = "https://www.pxweb.bfs.admin.ch/api/v1"

# Direct download URLs for key datasets
BFS_DATASETS = {
    # Official municipality register
    "gemeindeverzeichnis": "https://www.bfs.admin.ch/bfsstatic/dam/assets/29885681/master",
    # Population by municipality
    "population": "https://dam-api.bfs.admin.ch/hub/api/dam/assets/32007759/master",
    # Municipality mutations (mergers)
    "mutations": "https://www.bfs.admin.ch/bfsstatic/dam/assets/29885682/master",
}

# PXWeb query for population by municipality (px-x-0102010000_101)
POPULATION_PXWEB_QUERY = {
    "query": [
        {
            "code": "Gemeinde",
            "selection": {"filter": "all", "values": ["*"]},
        },
        {
            "code": "Bevölkerungstyp",
            "selection": {"filter": "item", "values": ["1"]},  # Ständige Wohnbevölkerung
        },
    ],
    "response": {"format": "json-stat2"},
}


async def download_file(url: str, filename: str) -> Path:
    """Download a file from a URL."""
    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    filepath = raw_dir / filename

    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        logger.info(f"Downloading {url} -> {filepath}")
        response = await client.get(url)
        response.raise_for_status()
        filepath.write_bytes(response.content)

    logger.info(f"Downloaded {filepath} ({filepath.stat().st_size / 1024:.1f} KB)")
    return filepath


def parse_gemeindeverzeichnis(filepath: Path) -> pd.DataFrame:
    """Parse the official BFS municipality register."""
    logger.info(f"Parsing municipality register: {filepath}")

    try:
        df = pd.read_excel(filepath, sheet_name=0, header=0)
    except Exception:
        df = pd.read_csv(filepath, sep="\t", encoding="utf-8")

    # Normalize column names
    col_map = {
        "GDENR": "bfs_number",
        "BFS Gde-nummer": "bfs_number",
        "GDENAME": "name",
        "Gemeindename": "name",
        "GDEKT": "canton_abbreviation",
        "Kanton": "canton_abbreviation",
        "GDEAREA": "area_km2",
        "Fläche in km²": "area_km2",
        "GDEPOP": "population",
        "Einwohner": "population",
        "GDEBZNR": "district_bfs",
        "Bezirks-Nr.": "district_bfs",
    }
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "bfs_number" in df.columns:
        df["bfs_number"] = pd.to_numeric(df["bfs_number"], errors="coerce")
        df = df.dropna(subset=["bfs_number"])
        df["bfs_number"] = df["bfs_number"].astype(int)
        df["is_active"] = True

    logger.info(f"Parsed {len(df)} municipalities from register")
    return df


def parse_population_data(filepath: Path) -> pd.DataFrame:
    """Parse BFS population statistics."""
    logger.info(f"Parsing population data: {filepath}")

    try:
        df = pd.read_excel(filepath, sheet_name=0, header=0)
    except Exception:
        df = pd.read_csv(filepath, sep=";", encoding="utf-8")

    # Try to identify and normalize columns
    col_map = {
        "BFS_NR": "municipality_bfs",
        "BFS Gde-nummer": "municipality_bfs",
        "Gemeinde_Nr": "municipality_bfs",
        "Jahr": "year",
        "Year": "year",
        "Bevölkerung": "population_total",
        "Population": "population_total",
        "Ständige Wohnbevölkerung": "population_total",
        "Schweizer": "population_swiss",
        "Ausländer": "population_foreign",
        "Männer": "population_male",
        "Frauen": "population_female",
        "Geburten": "births",
        "Todesfälle": "deaths",
        "Zuwanderung": "immigration",
        "Abwanderung": "emigration",
    }
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "municipality_bfs" in df.columns:
        df["municipality_bfs"] = pd.to_numeric(df["municipality_bfs"], errors="coerce")
        df = df.dropna(subset=["municipality_bfs"])
        df["municipality_bfs"] = df["municipality_bfs"].astype(int)

        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)

        # Calculate derived fields
        if "population_swiss" in df.columns and "population_foreign" in df.columns:
            total = df.get("population_total", df["population_swiss"] + df["population_foreign"])
            df["foreign_share"] = (df["population_foreign"] / total * 100).round(2)

        if "births" in df.columns and "deaths" in df.columns:
            df["natural_change"] = df["births"] - df["deaths"]

        if "immigration" in df.columns and "emigration" in df.columns:
            df["net_migration"] = df["immigration"] - df["emigration"]

        df["data_source"] = "bfs"

    logger.info(f"Parsed {len(df)} population records")
    return df


def parse_mutations(filepath: Path) -> pd.DataFrame:
    """Parse BFS municipality mutation (merger) data."""
    logger.info(f"Parsing municipality mutations: {filepath}")

    try:
        df = pd.read_excel(filepath, sheet_name=0, header=0)
    except Exception:
        df = pd.read_csv(filepath, sep="\t", encoding="utf-8")

    logger.info(f"Parsed {len(df)} mutation records")
    return df


def load_municipalities_to_db(df: pd.DataFrame, db_url: str):
    """Load municipality master data into PostgreSQL."""
    engine = create_engine(db_url)

    # Map canton abbreviations to canton IDs
    with engine.begin() as conn:
        cantons = pd.read_sql("SELECT id, abbreviation FROM cantons", conn)
    canton_map = dict(zip(cantons["abbreviation"], cantons["id"]))

    if "canton_abbreviation" in df.columns:
        df["canton_id"] = df["canton_abbreviation"].map(canton_map)
        df = df.dropna(subset=["canton_id"])
        df["canton_id"] = df["canton_id"].astype(int)

    db_columns = ["bfs_number", "name", "canton_id", "population", "area_km2", "is_active"]
    available = [c for c in db_columns if c in df.columns]
    df_insert = df[available].drop_duplicates(subset=["bfs_number"])

    with engine.begin() as conn:
        # Upsert: update existing, insert new
        for _, row in df_insert.iterrows():
            existing = conn.execute(
                text("SELECT id FROM municipalities WHERE bfs_number = :bfs"),
                {"bfs": int(row["bfs_number"])},
            ).fetchone()

            if existing:
                sets = ", ".join(f"{c} = :{c}" for c in available if c != "bfs_number")
                conn.execute(
                    text(f"UPDATE municipalities SET {sets} WHERE bfs_number = :bfs_number"),
                    row[available].to_dict(),
                )
            else:
                cols = ", ".join(available)
                vals = ", ".join(f":{c}" for c in available)
                conn.execute(
                    text(f"INSERT INTO municipalities ({cols}) VALUES ({vals})"),
                    row[available].to_dict(),
                )

    logger.info(f"Loaded {len(df_insert)} municipalities into database")


def load_demographic_data_to_db(df: pd.DataFrame, db_url: str):
    """Load demographic data into PostgreSQL."""
    engine = create_engine(db_url)

    db_columns = [
        "municipality_bfs", "year", "population_total", "population_swiss",
        "population_foreign", "foreign_share", "population_male", "population_female",
        "age_0_19", "age_20_39", "age_40_64", "age_65_plus",
        "dependency_ratio", "youth_ratio", "births", "deaths",
        "natural_change", "immigration", "emigration", "net_migration",
        "population_growth_rate", "data_source",
    ]
    available = [c for c in db_columns if c in df.columns]
    df_insert = df[available].copy()

    with engine.begin() as conn:
        for _, row in df_insert.iterrows():
            conn.execute(
                text("DELETE FROM demographic_data WHERE municipality_bfs = :bfs AND year = :yr"),
                {"bfs": int(row["municipality_bfs"]), "yr": int(row["year"])},
            )
        df_insert.to_sql("demographic_data", conn, if_exists="append", index=False, method="multi")

    logger.info(f"Loaded {len(df_insert)} demographic records into database")


async def run_bfs_pipeline(db_url: str):
    """Main ETL pipeline for BFS data."""
    logger.info("Starting BFS data ETL pipeline")

    # 1. Municipality register (master data)
    try:
        filepath = await download_file(
            BFS_DATASETS["gemeindeverzeichnis"],
            "bfs_gemeindeverzeichnis.xlsx",
        )
        df = parse_gemeindeverzeichnis(filepath)
        if not df.empty:
            load_municipalities_to_db(df, db_url)
    except Exception as e:
        logger.error(f"Failed to process municipality register: {e}")

    # 2. Population data
    try:
        filepath = await download_file(
            BFS_DATASETS["population"],
            "bfs_population.xlsx",
        )
        df = parse_population_data(filepath)
        if not df.empty and "year" in df.columns:
            load_demographic_data_to_db(df, db_url)
    except Exception as e:
        logger.error(f"Failed to process population data: {e}")

    # 3. Municipality mutations
    try:
        filepath = await download_file(
            BFS_DATASETS["mutations"],
            "bfs_mutations.xlsx",
        )
        parse_mutations(filepath)
        # TODO: Load mutations into municipality_mergers table
    except Exception as e:
        logger.warning(f"Failed to process mutations: {e}")

    logger.info("BFS ETL pipeline complete")
