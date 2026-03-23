"""
Time series analysis and trend forecasting for Swiss municipalities.

Provides:
- Trend detection (improving, stable, declining)
- Simple forecasting (linear regression + moving averages)
- Anomaly detection
"""

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats
from sqlalchemy import create_engine, text


def detect_trend(values: list[float], threshold: float = 0.05) -> dict:
    """
    Detect trend direction using linear regression.

    Returns dict with slope, direction, significance, and R².
    """
    if len(values) < 3:
        return {"direction": "insufficient_data", "confidence": 0}

    clean = [(i, v) for i, v in enumerate(values) if v is not None and not np.isnan(v)]
    if len(clean) < 3:
        return {"direction": "insufficient_data", "confidence": 0}

    x = np.array([c[0] for c in clean])
    y = np.array([c[1] for c in clean])

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    r_squared = r_value ** 2

    if p_value > threshold:
        direction = "stable"
    elif slope > 0:
        direction = "improving"
    else:
        direction = "declining"

    return {
        "direction": direction,
        "slope": round(float(slope), 4),
        "r_squared": round(float(r_squared), 4),
        "p_value": round(float(p_value), 6),
        "confidence": round(float(1 - p_value) * 100, 1),
    }


def forecast_linear(years: list[int], values: list[float], forecast_years: int = 3) -> list[dict]:
    """
    Simple linear regression forecast.
    """
    clean = [(y, v) for y, v in zip(years, values) if v is not None and not np.isnan(v)]
    if len(clean) < 3:
        return []

    x = np.array([c[0] for c in clean])
    y = np.array([c[1] for c in clean])

    slope, intercept, r_value, _, _ = stats.linregress(x, y)

    last_year = int(max(x))
    predictions = []
    for i in range(1, forecast_years + 1):
        pred_year = last_year + i
        pred_value = slope * pred_year + intercept
        predictions.append({
            "year": pred_year,
            "predicted_value": round(float(pred_value), 2),
            "confidence": round(float(r_value ** 2) * 100, 1),
        })

    return predictions


def detect_anomalies(values: list[float], z_threshold: float = 2.0) -> list[int]:
    """
    Detect anomalous years using z-score method.

    Returns list of indices where values are anomalous.
    """
    clean = [v for v in values if v is not None and not np.isnan(v)]
    if len(clean) < 5:
        return []

    arr = np.array(clean)
    z_scores = np.abs(stats.zscore(arr))

    return [i for i, z in enumerate(z_scores) if z > z_threshold]


def get_municipality_trends(
    bfs_number: int,
    db_url: str,
    metrics: list[str] | None = None,
) -> dict:
    """
    Analyze trends for a municipality across all key metrics.
    """
    if metrics is None:
        metrics = [
            "net_debt_per_capita",
            "self_financing_ratio",
            "tax_revenue_per_capita",
            "population_total",
            "population_growth_rate",
            "composite_score",
        ]

    engine = create_engine(db_url)
    results = {}

    with engine.connect() as conn:
        # Financial trends
        financial = pd.read_sql(
            text("SELECT * FROM financial_data WHERE municipality_bfs = :bfs ORDER BY year"),
            conn,
            params={"bfs": bfs_number},
        )

        demographic = pd.read_sql(
            text("SELECT * FROM demographic_data WHERE municipality_bfs = :bfs ORDER BY year"),
            conn,
            params={"bfs": bfs_number},
        )

        scores = pd.read_sql(
            text("SELECT * FROM composite_scores WHERE municipality_bfs = :bfs ORDER BY year"),
            conn,
            params={"bfs": bfs_number},
        )

    for metric in metrics:
        # Find the metric in the right dataframe
        for df, source in [(financial, "financial"), (demographic, "demographic"), (scores, "scores")]:
            if metric in df.columns and not df.empty:
                values = df[metric].tolist()
                years = df["year"].tolist()

                trend = detect_trend(values)
                forecast = forecast_linear(years, values)
                anomalies = detect_anomalies(values)

                results[metric] = {
                    "source": source,
                    "years": years,
                    "values": [float(v) if pd.notna(v) else None for v in values],
                    "trend": trend,
                    "forecast": forecast,
                    "anomaly_indices": anomalies,
                }
                break

    return results
