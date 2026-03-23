from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.financial import FinancialData
from app.api.schemas import FinancialDataResponse, TimeSeriesPoint

router = APIRouter()


@router.get("/{bfs_number}", response_model=list[FinancialDataResponse])
async def get_financial_data(
    bfs_number: int,
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(FinancialData)
        .where(FinancialData.municipality_bfs == bfs_number)
    )
    if year_from:
        query = query.where(FinancialData.year >= year_from)
    if year_to:
        query = query.where(FinancialData.year <= year_to)
    query = query.order_by(FinancialData.year)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{bfs_number}/timeseries/{metric}", response_model=list[TimeSeriesPoint])
async def get_financial_timeseries(
    bfs_number: int,
    metric: str,
    db: AsyncSession = Depends(get_db),
):
    allowed_metrics = {
        "total_revenue", "tax_revenue", "total_expenditure", "operating_result",
        "net_debt", "equity", "revenue_per_capita", "expenditure_per_capita",
        "net_debt_per_capita", "self_financing_ratio", "debt_ratio",
    }
    if metric not in allowed_metrics:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid metric. Allowed: {allowed_metrics}")

    column = getattr(FinancialData, metric)
    query = (
        select(FinancialData.year, column)
        .where(FinancialData.municipality_bfs == bfs_number)
        .order_by(FinancialData.year)
    )
    result = await db.execute(query)
    return [TimeSeriesPoint(year=row[0], value=float(row[1]) if row[1] else None) for row in result.all()]
