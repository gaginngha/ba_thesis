"""
Benchmark and comparison API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.analytics.benchmark import get_peer_group_stats, compare_municipalities

router = APIRouter()


@router.get("/{bfs_number}/peer-group")
async def get_peer_benchmark(
    bfs_number: int,
    year: Optional[int] = Query(None, description="Year (defaults to latest available)"),
    db: AsyncSession = Depends(get_db),
):
    """Get a municipality's benchmark against its peer group."""
    # Default to a recent year if not specified
    if year is None:
        year = 2022
    return get_peer_group_stats(bfs_number, year, settings.sync_database_url)


@router.get("/compare")
async def compare(
    bfs: str = Query(..., description="Comma-separated BFS numbers (e.g. 261,351,2701)"),
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Side-by-side comparison of multiple municipalities."""
    bfs_numbers = [int(b.strip()) for b in bfs.split(",") if b.strip().isdigit()]
    if len(bfs_numbers) < 2:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Provide at least 2 BFS numbers")
    if len(bfs_numbers) > 10:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Max 10 municipalities")

    if year is None:
        year = 2022

    return compare_municipalities(bfs_numbers, year, settings.sync_database_url)
