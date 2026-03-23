from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.municipality import Canton, Municipality
from app.api.schemas import CantonResponse, MunicipalityListItem, MunicipalityDetail

router = APIRouter()


@router.get("/", response_model=list[MunicipalityListItem])
async def list_municipalities(
    canton: Optional[str] = Query(None, description="Filter by canton abbreviation (e.g. ZH, BE)"),
    search: Optional[str] = Query(None, description="Search by name"),
    active_only: bool = Query(True, description="Only show active municipalities"),
    limit: int = Query(50, le=2500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Municipality, Canton.abbreviation)
        .join(Canton, Municipality.canton_id == Canton.id)
    )
    if active_only:
        query = query.where(Municipality.is_active.is_(True))
    if canton:
        query = query.where(Canton.abbreviation == canton.upper())
    if search:
        query = query.where(Municipality.name.ilike(f"%{search}%"))
    query = query.order_by(Municipality.name).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        MunicipalityListItem(
            bfs_number=muni.bfs_number,
            name=muni.name,
            canton_abbreviation=abbr,
            population=muni.population,
            municipality_type=muni.municipality_type,
            is_active=muni.is_active,
        )
        for muni, abbr in rows
    ]


@router.get("/count")
async def count_municipalities(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    query = select(func.count(Municipality.id))
    if active_only:
        query = query.where(Municipality.is_active.is_(True))
    result = await db.execute(query)
    return {"count": result.scalar()}


@router.get("/cantons", response_model=list[CantonResponse])
async def list_cantons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Canton).order_by(Canton.bfs_number))
    return result.scalars().all()


@router.get("/{bfs_number}", response_model=MunicipalityDetail)
async def get_municipality(bfs_number: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(Municipality)
        .options(joinedload(Municipality.canton))
        .where(Municipality.bfs_number == bfs_number)
    )
    result = await db.execute(query)
    muni = result.scalar_one_or_none()
    if not muni:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Municipality {bfs_number} not found")

    return MunicipalityDetail(
        bfs_number=muni.bfs_number,
        name=muni.name,
        canton=CantonResponse(
            bfs_number=muni.canton.bfs_number,
            abbreviation=muni.canton.abbreviation,
            name_de=muni.canton.name_de,
            name_fr=muni.canton.name_fr,
        ),
        population=muni.population,
        area_km2=float(muni.area_km2) if muni.area_km2 else None,
        altitude_m=muni.altitude_m,
        municipality_type=muni.municipality_type,
        is_active=muni.is_active,
    )
