from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EconomicData(Base):
    __tablename__ = "economic_data"
    __table_args__ = (
        UniqueConstraint("municipality_bfs", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_bfs: Mapped[int] = mapped_column(
        Integer, ForeignKey("municipalities.bfs_number"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    total_establishments: Mapped[Optional[int]] = mapped_column(Integer)
    total_employment: Mapped[Optional[int]] = mapped_column(Integer)
    full_time_equivalents: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))

    primary_sector_employment: Mapped[Optional[int]] = mapped_column(Integer)
    secondary_sector_employment: Mapped[Optional[int]] = mapped_column(Integer)
    tertiary_sector_employment: Mapped[Optional[int]] = mapped_column(Integer)

    employment_per_capita: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    sector_diversity_index: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    data_source: Mapped[str] = mapped_column(String(50), default="bfs_statent")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    municipality: Mapped["Municipality"] = relationship(back_populates="economic_data")


from app.models.municipality import Municipality  # noqa: E402, F811
