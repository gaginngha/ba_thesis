from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.municipality import Canton, Municipality
from app.models.scores import CompositeScore
from app.api.schemas import CompositeScoreResponse

router = APIRouter()


@router.get("/rankings", response_model=list[CompositeScoreResponse])
async def get_rankings(
    year: Optional[int] = Query(None, description="Year (defaults to latest)"),
    canton: Optional[str] = Query(None, description="Filter by canton abbreviation"),
    peer_group: Optional[str] = Query(None, description="Filter by peer group"),
    sort_by: str = Query("composite_score", description="Sort field"),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(CompositeScore, Municipality.name, Canton.abbreviation)
        .join(Municipality, CompositeScore.municipality_bfs == Municipality.bfs_number)
        .join(Canton, Municipality.canton_id == Canton.id)
    )

    if year:
        query = query.where(CompositeScore.year == year)
    if canton:
        query = query.where(Canton.abbreviation == canton.upper())
    if peer_group:
        query = query.where(CompositeScore.peer_group == peer_group)

    sort_column = getattr(CompositeScore, sort_by, CompositeScore.composite_score)
    query = query.order_by(sort_column.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        CompositeScoreResponse(
            municipality_bfs=score.municipality_bfs,
            municipality_name=name,
            canton_abbreviation=abbr,
            year=score.year,
            financial_health_score=float(score.financial_health_score) if score.financial_health_score else None,
            tax_attractiveness_score=float(score.tax_attractiveness_score) if score.tax_attractiveness_score else None,
            demographic_vitality_score=float(score.demographic_vitality_score) if score.demographic_vitality_score else None,
            economic_strength_score=float(score.economic_strength_score) if score.economic_strength_score else None,
            composite_score=float(score.composite_score) if score.composite_score else None,
            peer_group=score.peer_group,
            peer_group_rank=score.peer_group_rank,
            national_rank=score.national_rank,
            cantonal_rank=score.cantonal_rank,
        )
        for score, name, abbr in rows
    ]


@router.get("/{bfs_number}", response_model=list[CompositeScoreResponse])
async def get_municipality_scores(
    bfs_number: int,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(CompositeScore, Municipality.name, Canton.abbreviation)
        .join(Municipality, CompositeScore.municipality_bfs == Municipality.bfs_number)
        .join(Canton, Municipality.canton_id == Canton.id)
        .where(CompositeScore.municipality_bfs == bfs_number)
        .order_by(CompositeScore.year)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        CompositeScoreResponse(
            municipality_bfs=score.municipality_bfs,
            municipality_name=name,
            canton_abbreviation=abbr,
            year=score.year,
            financial_health_score=float(score.financial_health_score) if score.financial_health_score else None,
            tax_attractiveness_score=float(score.tax_attractiveness_score) if score.tax_attractiveness_score else None,
            demographic_vitality_score=float(score.demographic_vitality_score) if score.demographic_vitality_score else None,
            economic_strength_score=float(score.economic_strength_score) if score.economic_strength_score else None,
            composite_score=float(score.composite_score) if score.composite_score else None,
            peer_group=score.peer_group,
            peer_group_rank=score.peer_group_rank,
            national_rank=score.national_rank,
            cantonal_rank=score.cantonal_rank,
        )
        for score, name, abbr in rows
    ]
