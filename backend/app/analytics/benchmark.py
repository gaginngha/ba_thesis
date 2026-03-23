"""
Peer group benchmarking for Swiss municipalities.

Provides comparison tools to benchmark municipalities against:
- Their peer group (by size/type)
- Their canton
- National averages
"""

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text


def get_peer_group_stats(
    bfs_number: int,
    year: int,
    db_url: str,
) -> dict:
    """
    Get a municipality's position relative to its peer group.

    Returns dict with the municipality's scores, peer group averages,
    percentile ranks, and top/bottom peers.
    """
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Get target municipality's scores
        target = pd.read_sql(
            text("""
                SELECT cs.*, m.name, m.population, c.abbreviation as canton
                FROM composite_scores cs
                JOIN municipalities m ON cs.municipality_bfs = m.bfs_number
                JOIN cantons c ON m.canton_id = c.id
                WHERE cs.municipality_bfs = :bfs AND cs.year = :year
                ORDER BY cs.scoring_version DESC LIMIT 1
            """),
            conn,
            params={"bfs": bfs_number, "year": year},
        )

        if target.empty:
            return {"error": f"No scores found for municipality {bfs_number} in {year}"}

        peer_group = target.iloc[0]["peer_group"]

        # Get all scores in same peer group
        peers = pd.read_sql(
            text("""
                SELECT cs.*, m.name, m.population, c.abbreviation as canton
                FROM composite_scores cs
                JOIN municipalities m ON cs.municipality_bfs = m.bfs_number
                JOIN cantons c ON m.canton_id = c.id
                WHERE cs.peer_group = :pg AND cs.year = :year
                  AND cs.scoring_version = (SELECT MAX(scoring_version) FROM composite_scores WHERE year = :year)
            """),
            conn,
            params={"pg": peer_group, "year": year},
        )

    score_cols = [
        "financial_health_score", "tax_attractiveness_score",
        "demographic_vitality_score", "economic_strength_score", "composite_score",
    ]

    target_row = target.iloc[0]

    return {
        "municipality": {
            "bfs_number": int(target_row["municipality_bfs"]),
            "name": target_row["name"],
            "canton": target_row["canton"],
            "population": int(target_row["population"]) if pd.notna(target_row["population"]) else None,
        },
        "year": year,
        "peer_group": peer_group,
        "peer_group_size": len(peers),
        "scores": {col: float(target_row[col]) if pd.notna(target_row[col]) else None for col in score_cols},
        "peer_group_avg": {col: round(float(peers[col].mean()), 2) if not peers[col].isna().all() else None for col in score_cols},
        "peer_group_median": {col: round(float(peers[col].median()), 2) if not peers[col].isna().all() else None for col in score_cols},
        "percentile_rank": {
            col: round(float((peers[col] < target_row[col]).sum() / len(peers) * 100), 1)
            if pd.notna(target_row[col]) and not peers[col].isna().all()
            else None
            for col in score_cols
        },
        "top_5_peers": peers.nlargest(5, "composite_score")[["municipality_bfs", "name", "canton", "composite_score"]].to_dict("records"),
    }


def compare_municipalities(
    bfs_numbers: list[int],
    year: int,
    db_url: str,
) -> list[dict]:
    """
    Side-by-side comparison of multiple municipalities.
    """
    engine = create_engine(db_url)

    placeholders = ", ".join(f":bfs_{i}" for i in range(len(bfs_numbers)))
    params = {f"bfs_{i}": bfs for i, bfs in enumerate(bfs_numbers)}
    params["year"] = year

    with engine.connect() as conn:
        df = pd.read_sql(
            text(f"""
                SELECT cs.*, m.name, m.population, c.abbreviation as canton
                FROM composite_scores cs
                JOIN municipalities m ON cs.municipality_bfs = m.bfs_number
                JOIN cantons c ON m.canton_id = c.id
                WHERE cs.municipality_bfs IN ({placeholders}) AND cs.year = :year
                ORDER BY cs.composite_score DESC
            """),
            conn,
            params=params,
        )

    results = []
    for _, row in df.iterrows():
        results.append({
            "bfs_number": int(row["municipality_bfs"]),
            "name": row["name"],
            "canton": row["canton"],
            "population": int(row["population"]) if pd.notna(row["population"]) else None,
            "composite_score": float(row["composite_score"]) if pd.notna(row["composite_score"]) else None,
            "financial_health": float(row["financial_health_score"]) if pd.notna(row["financial_health_score"]) else None,
            "tax_attractiveness": float(row["tax_attractiveness_score"]) if pd.notna(row["tax_attractiveness_score"]) else None,
            "demographic_vitality": float(row["demographic_vitality_score"]) if pd.notna(row["demographic_vitality_score"]) else None,
            "economic_strength": float(row["economic_strength_score"]) if pd.notna(row["economic_strength_score"]) else None,
            "peer_group": row["peer_group"],
            "national_rank": int(row["national_rank"]) if pd.notna(row["national_rank"]) else None,
        })

    return results
