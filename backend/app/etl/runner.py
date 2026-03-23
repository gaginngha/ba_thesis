"""
ETL runner — orchestrates all data pipelines.

Usage:
    python -m app.etl.runner              # Run all pipelines
    python -m app.etl.runner efv          # Run only EFV pipeline
    python -m app.etl.runner bfs          # Run only BFS pipeline
    python -m app.etl.runner geo          # Run only geospatial pipeline
    python -m app.etl.runner scores 2022  # Calculate composite scores for a year
"""

import asyncio
import sys

from loguru import logger

from app.core.config import settings
from app.etl.efv import run_efv_pipeline
from app.etl.bfs import run_bfs_pipeline
from app.etl.geo import run_geo_pipeline
from app.analytics.composite import calculate_composite_scores, save_composite_scores


async def run_all():
    db_url = settings.sync_database_url
    logger.info(f"Running all ETL pipelines (DB: {db_url})")

    await run_bfs_pipeline(db_url)    # Municipality master data first
    await run_efv_pipeline(db_url)    # Financial data second (needs municipality FKs)
    await run_geo_pipeline(db_url)    # Geospatial data (needs municipalities)

    # Calculate composite scores for recent years
    for year in range(2018, 2024):
        try:
            df = calculate_composite_scores(year, db_url)
            if not df.empty:
                save_composite_scores(df, db_url)
        except Exception as e:
            logger.warning(f"Could not calculate scores for {year}: {e}")

    logger.info("All ETL pipelines complete")


async def main():
    pipeline = sys.argv[1] if len(sys.argv) > 1 else "all"
    db_url = settings.sync_database_url

    if pipeline == "efv":
        await run_efv_pipeline(db_url)
    elif pipeline == "bfs":
        await run_bfs_pipeline(db_url)
    elif pipeline == "geo":
        await run_geo_pipeline(db_url)
    elif pipeline == "scores":
        year = int(sys.argv[2]) if len(sys.argv) > 2 else 2022
        df = calculate_composite_scores(year, db_url)
        if not df.empty:
            save_composite_scores(df, db_url)
    elif pipeline == "all":
        await run_all()
    else:
        logger.error(f"Unknown pipeline: {pipeline}. Use: efv, bfs, geo, scores, all")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
