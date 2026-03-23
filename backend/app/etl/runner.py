"""
ETL runner — orchestrates all data pipelines.

Usage:
    python -m app.etl.runner          # Run all pipelines
    python -m app.etl.runner efv      # Run only EFV pipeline
    python -m app.etl.runner bfs      # Run only BFS pipeline
"""

import asyncio
import sys

from loguru import logger

from app.core.config import settings
from app.etl.efv import run_efv_pipeline
from app.etl.bfs import run_bfs_pipeline


async def run_all():
    db_url = settings.sync_database_url
    logger.info(f"Running all ETL pipelines (DB: {db_url})")

    await run_bfs_pipeline(db_url)    # Municipality master data first
    await run_efv_pipeline(db_url)    # Financial data second (needs municipality FKs)

    logger.info("All ETL pipelines complete")


async def main():
    pipeline = sys.argv[1] if len(sys.argv) > 1 else "all"
    db_url = settings.sync_database_url

    if pipeline == "efv":
        await run_efv_pipeline(db_url)
    elif pipeline == "bfs":
        await run_bfs_pipeline(db_url)
    elif pipeline == "all":
        await run_all()
    else:
        logger.error(f"Unknown pipeline: {pipeline}. Use: efv, bfs, all")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
