from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.demographic import DemographicData
from app.api.schemas import DemographicResponse, TimeSeriesPoint

router = APIRouter()


@router.get("/{bfs_number}", response_model=list[DemographicResponse])
async def get_demographic_data(
    bfs_number: int,
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(DemographicData)
        .where(DemographicData.municipality_bfs == bfs_number)
    )
    if year_from:
        query = query.where(DemographicData.year >= year_from)
    if year_to:
        query = query.where(DemographicData.year <= year_to)
    query = query.order_by(DemographicData.year)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{bfs_number}/timeseries/{metric}", response_model=list[TimeSeriesPoint])
async def get_demographic_timeseries(
    bfs_number: int,
    metric: str,
    db: AsyncSession = Depends(get_db),
):
    allowed_metrics = {
        "population_total", "population_swiss", "population_foreign",
        "foreign_share", "age_0_19", "age_65_plus", "dependency_ratio",
        "births", "deaths", "net_migration", "population_growth_rate",
    }
    if metric not in allowed_metrics:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid metric. Allowed: {allowed_metrics}")

    column = getattr(DemographicData, metric)
    query = (
        select(DemographicData.year, column)
        .where(DemographicData.municipality_bfs == bfs_number)
        .order_by(DemographicData.year)
    )
    result = await db.execute(query)
    return [TimeSeriesPoint(year=row[0], value=float(row[1]) if row[1] else None) for row in result.all()]
