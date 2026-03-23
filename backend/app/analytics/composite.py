"""
Composite scoring engine for Swiss municipalities.

Calculates a multi-dimensional attractiveness/health score by combining:
- Financial health (30%)
- Tax attractiveness (20%)
- Demographic vitality (20%)
- Economic strength (15%)
- Infrastructure quality (15%)

Each sub-score is normalized to 0-100 using min-max scaling within peer groups.
"""

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text

from app.core.config import settings


def normalize_metric(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """Normalize a metric to 0-100 scale using min-max scaling."""
    if series.isna().all():
        return series
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(50.0, index=series.index)
    normalized = (series - min_val) / (max_val - min_val) * 100
    if not higher_is_better:
        normalized = 100 - normalized
    return normalized


def calculate_financial_health(df: pd.DataFrame) -> pd.Series:
    """
    Financial health sub-score based on:
    - Self-financing ratio (higher = better)
    - Net debt per capita (lower = better)
    - Operating result (higher = better)
    - Debt ratio (lower = better)
    """
    scores = pd.DataFrame(index=df.index)

    if "self_financing_ratio" in df.columns:
        scores["sfr"] = normalize_metric(df["self_financing_ratio"], higher_is_better=True)
    if "net_debt_per_capita" in df.columns:
        scores["ndc"] = normalize_metric(df["net_debt_per_capita"], higher_is_better=False)
    if "operating_result" in df.columns:
        scores["opr"] = normalize_metric(df["operating_result"], higher_is_better=True)
    if "debt_ratio" in df.columns:
        scores["dr"] = normalize_metric(df["debt_ratio"], higher_is_better=False)

    if scores.empty:
        return pd.Series(np.nan, index=df.index)

    return scores.mean(axis=1).round(2)


def calculate_tax_attractiveness(df: pd.DataFrame) -> pd.Series:
    """
    Tax attractiveness sub-score based on:
    - Tax multiplier (lower = more attractive)
    - Income tax index (lower = more attractive)
    """
    scores = pd.DataFrame(index=df.index)

    if "tax_multiplier" in df.columns:
        scores["tm"] = normalize_metric(df["tax_multiplier"], higher_is_better=False)
    if "income_tax_index" in df.columns:
        scores["iti"] = normalize_metric(df["income_tax_index"], higher_is_better=False)

    if scores.empty:
        return pd.Series(np.nan, index=df.index)

    return scores.mean(axis=1).round(2)


def calculate_demographic_vitality(df: pd.DataFrame) -> pd.Series:
    """
    Demographic vitality sub-score based on:
    - Population growth rate (higher = better)
    - Youth ratio (higher = better)
    - Net migration (higher = better)
    - Dependency ratio (lower = better)
    """
    scores = pd.DataFrame(index=df.index)

    if "population_growth_rate" in df.columns:
        scores["pgr"] = normalize_metric(df["population_growth_rate"], higher_is_better=True)
    if "youth_ratio" in df.columns:
        scores["yr"] = normalize_metric(df["youth_ratio"], higher_is_better=True)
    if "net_migration" in df.columns:
        scores["nm"] = normalize_metric(df["net_migration"], higher_is_better=True)
    if "dependency_ratio" in df.columns:
        scores["dep"] = normalize_metric(df["dependency_ratio"], higher_is_better=False)

    if scores.empty:
        return pd.Series(np.nan, index=df.index)

    return scores.mean(axis=1).round(2)


def calculate_economic_strength(df: pd.DataFrame) -> pd.Series:
    """
    Economic strength sub-score based on:
    - Employment per capita (higher = better)
    - Sector diversity index (higher = better)
    - Total establishments (higher = better)
    """
    scores = pd.DataFrame(index=df.index)

    if "employment_per_capita" in df.columns:
        scores["epc"] = normalize_metric(df["employment_per_capita"], higher_is_better=True)
    if "sector_diversity_index" in df.columns:
        scores["sdi"] = normalize_metric(df["sector_diversity_index"], higher_is_better=True)

    if scores.empty:
        return pd.Series(np.nan, index=df.index)

    return scores.mean(axis=1).round(2)


def assign_peer_group(population: int) -> str:
    """Assign a peer group based on municipality size."""
    if population is None:
        return "unknown"
    if population >= 50000:
        return "city_large"
    if population >= 20000:
        return "city_medium"
    if population >= 10000:
        return "urban"
    if population >= 5000:
        return "suburban"
    if population >= 2000:
        return "rural_large"
    return "rural_small"


def calculate_composite_scores(year: int, db_url: str) -> pd.DataFrame:
    """
    Calculate composite scores for all municipalities for a given year.

    Returns DataFrame with columns: municipality_bfs, year, and all score fields.
    """
    engine = create_engine(db_url)
    logger.info(f"Calculating composite scores for year {year}")

    # Load all data for the year
    with engine.connect() as conn:
        municipalities = pd.read_sql(
            text("SELECT bfs_number, population FROM municipalities WHERE is_active = TRUE"),
            conn,
        )
        financial = pd.read_sql(
            text("SELECT * FROM financial_data WHERE year = :year"),
            conn,
            params={"year": year},
        )
        tax = pd.read_sql(
            text("SELECT * FROM tax_data WHERE year = :year"),
            conn,
            params={"year": year},
        )
        demographic = pd.read_sql(
            text("SELECT * FROM demographic_data WHERE year = :year"),
            conn,
            params={"year": year},
        )
        economic = pd.read_sql(
            text("SELECT * FROM economic_data WHERE year = :year"),
            conn,
            params={"year": year},
        )

    # Merge all data on municipality BFS number
    df = municipalities.rename(columns={"bfs_number": "municipality_bfs"})
    if not financial.empty:
        df = df.merge(financial, on="municipality_bfs", how="left", suffixes=("", "_fin"))
    if not tax.empty:
        df = df.merge(tax, on="municipality_bfs", how="left", suffixes=("", "_tax"))
    if not demographic.empty:
        df = df.merge(demographic, on="municipality_bfs", how="left", suffixes=("", "_dem"))
    if not economic.empty:
        df = df.merge(economic, on="municipality_bfs", how="left", suffixes=("", "_eco"))

    # Calculate sub-scores
    df["financial_health_score"] = calculate_financial_health(df)
    df["tax_attractiveness_score"] = calculate_tax_attractiveness(df)
    df["demographic_vitality_score"] = calculate_demographic_vitality(df)
    df["economic_strength_score"] = calculate_economic_strength(df)

    # Calculate weighted composite score
    w = settings
    df["composite_score"] = (
        df["financial_health_score"].fillna(0) * w.weight_financial
        + df["tax_attractiveness_score"].fillna(0) * w.weight_tax
        + df["demographic_vitality_score"].fillna(0) * w.weight_demographic
        + df["economic_strength_score"].fillna(0) * w.weight_economic
    ).round(2)

    # Assign peer groups and rankings
    df["peer_group"] = df["population"].apply(assign_peer_group)
    df["year"] = year
    df["scoring_version"] = "v1"

    # National ranking
    df["national_rank"] = df["composite_score"].rank(ascending=False, method="min").astype("Int64")

    # Cantonal ranking (need canton info)
    with engine.connect() as conn:
        canton_map = pd.read_sql(
            text("""
                SELECT m.bfs_number as municipality_bfs, c.abbreviation as canton
                FROM municipalities m JOIN cantons c ON m.canton_id = c.id
            """),
            conn,
        )
    df = df.merge(canton_map, on="municipality_bfs", how="left")
    df["cantonal_rank"] = df.groupby("canton")["composite_score"].rank(ascending=False, method="min").astype("Int64")

    # Peer group ranking
    df["peer_group_rank"] = df.groupby("peer_group")["composite_score"].rank(ascending=False, method="min").astype("Int64")

    # Select output columns
    output_cols = [
        "municipality_bfs", "year", "financial_health_score", "tax_attractiveness_score",
        "demographic_vitality_score", "economic_strength_score", "composite_score",
        "peer_group", "peer_group_rank", "national_rank", "cantonal_rank", "scoring_version",
    ]
    result = df[output_cols]

    logger.info(f"Calculated scores for {len(result)} municipalities (year {year})")
    return result


def save_composite_scores(df: pd.DataFrame, db_url: str):
    """Save composite scores to database."""
    engine = create_engine(db_url)

    with engine.begin() as conn:
        # Clear existing scores for this year/version
        if not df.empty:
            year = int(df["year"].iloc[0])
            version = df["scoring_version"].iloc[0]
            conn.execute(
                text("DELETE FROM composite_scores WHERE year = :year AND scoring_version = :version"),
                {"year": year, "version": version},
            )
        df.to_sql("composite_scores", conn, if_exists="append", index=False, method="multi")

    logger.info(f"Saved {len(df)} composite scores to database")
