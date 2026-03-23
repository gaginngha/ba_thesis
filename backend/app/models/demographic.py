from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DemographicData(Base):
    __tablename__ = "demographic_data"
    __table_args__ = (
        UniqueConstraint("municipality_bfs", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_bfs: Mapped[int] = mapped_column(
        Integer, ForeignKey("municipalities.bfs_number"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    population_total: Mapped[Optional[int]] = mapped_column(Integer)
    population_swiss: Mapped[Optional[int]] = mapped_column(Integer)
    population_foreign: Mapped[Optional[int]] = mapped_column(Integer)
    foreign_share: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    population_male: Mapped[Optional[int]] = mapped_column(Integer)
    population_female: Mapped[Optional[int]] = mapped_column(Integer)

    # Age structure
    age_0_19: Mapped[Optional[int]] = mapped_column(Integer)
    age_20_39: Mapped[Optional[int]] = mapped_column(Integer)
    age_40_64: Mapped[Optional[int]] = mapped_column(Integer)
    age_65_plus: Mapped[Optional[int]] = mapped_column(Integer)
    dependency_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    youth_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    # Movement
    births: Mapped[Optional[int]] = mapped_column(Integer)
    deaths: Mapped[Optional[int]] = mapped_column(Integer)
    natural_change: Mapped[Optional[int]] = mapped_column(Integer)
    immigration: Mapped[Optional[int]] = mapped_column(Integer)
    emigration: Mapped[Optional[int]] = mapped_column(Integer)
    net_migration: Mapped[Optional[int]] = mapped_column(Integer)
    population_growth_rate: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    data_source: Mapped[str] = mapped_column(String(50), default="bfs")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    municipality: Mapped["Municipality"] = relationship(back_populates="demographic_data")


from app.models.municipality import Municipality  # noqa: E402, F811
