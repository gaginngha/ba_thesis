from datetime import date, datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Canton(Base):
    __tablename__ = "cantons"

    id: Mapped[int] = mapped_column(primary_key=True)
    bfs_number: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    name_de: Mapped[str] = mapped_column(String(100), nullable=False)
    name_fr: Mapped[Optional[str]] = mapped_column(String(100))
    name_it: Mapped[Optional[str]] = mapped_column(String(100))
    name_rm: Mapped[Optional[str]] = mapped_column(String(100))

    municipalities: Mapped[list["Municipality"]] = relationship(back_populates="canton")
    districts: Mapped[list["District"]] = relationship(back_populates="canton")


class District(Base):
    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(primary_key=True)
    bfs_number: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    name_de: Mapped[str] = mapped_column(String(200), nullable=False)
    canton_id: Mapped[int] = mapped_column(ForeignKey("cantons.id"), nullable=False)

    canton: Mapped["Canton"] = relationship(back_populates="districts")


class Municipality(Base):
    __tablename__ = "municipalities"

    id: Mapped[int] = mapped_column(primary_key=True)
    bfs_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    canton_id: Mapped[int] = mapped_column(ForeignKey("cantons.id"), nullable=False)
    district_id: Mapped[Optional[int]] = mapped_column(ForeignKey("districts.id"))
    population: Mapped[Optional[int]] = mapped_column(Integer)
    area_km2: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    altitude_m: Mapped[Optional[int]] = mapped_column(Integer)
    municipality_type: Mapped[Optional[str]] = mapped_column(String(50))
    geometry = mapped_column(Geometry("MULTIPOLYGON", srid=2056), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    merged_into_bfs: Mapped[Optional[int]] = mapped_column(Integer)
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_until: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    canton: Mapped["Canton"] = relationship(back_populates="municipalities")
    financial_data: Mapped[list["FinancialData"]] = relationship(back_populates="municipality")
    demographic_data: Mapped[list["DemographicData"]] = relationship(back_populates="municipality")
    economic_data: Mapped[list["EconomicData"]] = relationship(back_populates="municipality")
    composite_scores: Mapped[list["CompositeScore"]] = relationship(back_populates="municipality")


# Avoid circular imports
from app.models.financial import FinancialData  # noqa: E402
from app.models.demographic import DemographicData  # noqa: E402
from app.models.economic import EconomicData  # noqa: E402
from app.models.scores import CompositeScore  # noqa: E402
