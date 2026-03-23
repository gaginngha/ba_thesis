"""
Trend analysis and forecasting API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.analytics.forecast import (
    detect_trend,
    forecast_linear,
    detect_anomalies,
    get_municipality_trends,
)
from app.models.financial import FinancialData
from app.models.demographic import DemographicData
from app.models.scores import CompositeScore

router = APIRouter()


@router.get("/{bfs_number}")
async def get_trends(
    bfs_number: int,
    metrics: Optional[str] = Query(
        None,
        description="Comma-separated metrics (e.g. net_debt_per_capita,population_total)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Full trend analysis for a municipality across key metrics."""
    metric_list = metrics.split(",") if metrics else None
    result = get_municipality_trends(bfs_number, settings.sync_database_url, metric_list)
    return result


@router.get("/{bfs_number}/forecast/{metric}")
async def get_forecast(
    bfs_number: int,
    metric: str,
    forecast_years: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Get forecast for a specific metric."""
    # Determine which table holds the metric
    financial_metrics = {
        "total_revenue", "tax_revenue", "total_expenditure", "operating_result",
        "net_debt", "equity", "revenue_per_capita", "expenditure_per_capita",
        "net_debt_per_capita", "self_financing_ratio", "debt_ratio",
        "tax_revenue_per_capita", "self_financing_capacity",
    }
    demographic_metrics = {
        "population_total", "population_swiss", "population_foreign",
        "foreign_share", "births", "deaths", "net_migration",
        "population_growth_rate", "dependency_ratio",
    }
    score_metrics = {
        "composite_score", "financial_health_score", "tax_attractiveness_score",
        "demographic_vitality_score", "economic_strength_score",
    }

    years = []
    values = []

    if metric in financial_metrics:
        column = getattr(FinancialData, metric, None)
        if column is None:
            return {"error": f"Unknown metric: {metric}"}
        query = (
            select(FinancialData.year, column)
            .where(FinancialData.municipality_bfs == bfs_number)
            .order_by(FinancialData.year)
        )
        result = await db.execute(query)
        for row in result.all():
            years.append(row[0])
            values.append(float(row[1]) if row[1] is not None else None)

    elif metric in demographic_metrics:
        column = getattr(DemographicData, metric, None)
        if column is None:
            return {"error": f"Unknown metric: {metric}"}
        query = (
            select(DemographicData.year, column)
            .where(DemographicData.municipality_bfs == bfs_number)
            .order_by(DemographicData.year)
        )
        result = await db.execute(query)
        for row in result.all():
            years.append(row[0])
            values.append(float(row[1]) if row[1] is not None else None)

    elif metric in score_metrics:
        column = getattr(CompositeScore, metric, None)
        if column is None:
            return {"error": f"Unknown metric: {metric}"}
        query = (
            select(CompositeScore.year, column)
            .where(CompositeScore.municipality_bfs == bfs_number)
            .order_by(CompositeScore.year)
        )
        result = await db.execute(query)
        for row in result.all():
            years.append(row[0])
            values.append(float(row[1]) if row[1] is not None else None)

    else:
        return {"error": f"Unknown metric: {metric}"}

    clean_values = [v for v in values if v is not None]
    if len(clean_values) < 3:
        return {
            "metric": metric,
            "municipality_bfs": bfs_number,
            "historical": [{"year": y, "value": v} for y, v in zip(years, values)],
            "trend": {"direction": "insufficient_data", "confidence": 0},
            "forecast": [],
            "anomalies": [],
        }

    trend = detect_trend(values)
    forecast = forecast_linear(years, values, forecast_years)
    anomaly_indices = detect_anomalies(values)
    anomalies = [
        {"year": years[i], "value": values[i]}
        for i in anomaly_indices
        if i < len(years)
    ]

    return {
        "metric": metric,
        "municipality_bfs": bfs_number,
        "historical": [{"year": y, "value": v} for y, v in zip(years, values)],
        "trend": trend,
        "forecast": forecast,
        "anomalies": anomalies,
    }
