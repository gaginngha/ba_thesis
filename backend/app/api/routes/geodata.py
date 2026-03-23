"""
GeoJSON API endpoints for municipality boundaries and choropleth data.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.municipality import Canton, Municipality
from app.models.scores import CompositeScore
from app.models.financial import FinancialData

router = APIRouter()


@router.get("/municipalities")
async def get_municipality_boundaries(
    canton: Optional[str] = Query(None, description="Filter by canton abbreviation"),
    simplify: float = Query(0.001, description="Geometry simplification tolerance"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get GeoJSON FeatureCollection of municipality boundaries.
    Uses PostGIS ST_AsGeoJSON and ST_Simplify for efficient rendering.
    """
    canton_filter = ""
    params = {"simplify": simplify}
    if canton:
        canton_filter = "AND c.abbreviation = :canton"
        params["canton"] = canton.upper()

    query = text(f"""
        SELECT
            m.bfs_number,
            m.name,
            c.abbreviation as canton,
            m.population,
            ST_AsGeoJSON(
                ST_Transform(
                    ST_Simplify(m.geometry, :simplify),
                    4326
                )
            ) as geojson
        FROM municipalities m
        JOIN cantons c ON m.canton_id = c.id
        WHERE m.is_active = TRUE
          AND m.geometry IS NOT NULL
          {canton_filter}
        ORDER BY m.name
    """)

    result = await db.execute(query, params)
    rows = result.all()

    features = []
    for row in rows:
        if row.geojson:
            import json
            features.append({
                "type": "Feature",
                "properties": {
                    "bfs_number": row.bfs_number,
                    "name": row.name,
                    "canton": row.canton,
                    "population": row.population,
                },
                "geometry": json.loads(row.geojson),
            })

    return JSONResponse(content={
        "type": "FeatureCollection",
        "features": features,
    })


@router.get("/choropleth/{metric}")
async def get_choropleth_data(
    metric: str,
    year: Optional[int] = Query(None),
    canton: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Get choropleth data: municipality boundaries with a specific metric value.
    Returns GeoJSON with the metric value embedded in each feature's properties.
    """
    # Map metrics to their source tables and columns
    metric_sources = {
        # Composite scores
        "composite_score": ("composite_scores", "composite_score"),
        "financial_health_score": ("composite_scores", "financial_health_score"),
        "tax_attractiveness_score": ("composite_scores", "tax_attractiveness_score"),
        "demographic_vitality_score": ("composite_scores", "demographic_vitality_score"),
        "economic_strength_score": ("composite_scores", "economic_strength_score"),
        # Financial
        "net_debt_per_capita": ("financial_data", "net_debt_per_capita"),
        "revenue_per_capita": ("financial_data", "revenue_per_capita"),
        "self_financing_ratio": ("financial_data", "self_financing_ratio"),
        "debt_ratio": ("financial_data", "debt_ratio"),
        "tax_revenue_per_capita": ("financial_data", "tax_revenue_per_capita"),
        # Demographic
        "population_total": ("demographic_data", "population_total"),
        "population_growth_rate": ("demographic_data", "population_growth_rate"),
        "foreign_share": ("demographic_data", "foreign_share"),
        "dependency_ratio": ("demographic_data", "dependency_ratio"),
    }

    if metric not in metric_sources:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric. Available: {list(metric_sources.keys())}",
        )

    table, column = metric_sources[metric]
    yr = year or 2022

    canton_filter = ""
    params: dict = {"year": yr}
    if canton:
        canton_filter = "AND c.abbreviation = :canton"
        params["canton"] = canton.upper()

    query = text(f"""
        SELECT
            m.bfs_number,
            m.name,
            c.abbreviation as canton,
            m.population,
            d.{column} as metric_value,
            ST_AsGeoJSON(
                ST_Transform(
                    ST_Simplify(m.geometry, 0.001),
                    4326
                )
            ) as geojson
        FROM municipalities m
        JOIN cantons c ON m.canton_id = c.id
        LEFT JOIN {table} d ON d.municipality_bfs = m.bfs_number AND d.year = :year
        WHERE m.is_active = TRUE
          AND m.geometry IS NOT NULL
          {canton_filter}
        ORDER BY m.name
    """)

    result = await db.execute(query, params)
    rows = result.all()

    values = [float(r.metric_value) for r in rows if r.metric_value is not None]
    stats = {}
    if values:
        stats = {
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "count": len(values),
        }

    features = []
    for row in rows:
        if row.geojson:
            import json
            features.append({
                "type": "Feature",
                "properties": {
                    "bfs_number": row.bfs_number,
                    "name": row.name,
                    "canton": row.canton,
                    "population": row.population,
                    "value": float(row.metric_value) if row.metric_value is not None else None,
                },
                "geometry": json.loads(row.geojson),
            })

    return JSONResponse(content={
        "type": "FeatureCollection",
        "metadata": {
            "metric": metric,
            "year": yr,
            "stats": stats,
        },
        "features": features,
    })
