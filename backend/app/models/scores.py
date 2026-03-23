from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompositeScore(Base):
    __tablename__ = "composite_scores"
    __table_args__ = (
        UniqueConstraint("municipality_bfs", "year", "scoring_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_bfs: Mapped[int] = mapped_column(
        Integer, ForeignKey("municipalities.bfs_number"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Sub-scores (0-100)
    financial_health_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    tax_attractiveness_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    demographic_vitality_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    economic_strength_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))

    # Overall
    composite_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))

    # Rankings
    peer_group: Mapped[Optional[str]] = mapped_column(String(50))
    peer_group_rank: Mapped[Optional[int]] = mapped_column(Integer)
    national_rank: Mapped[Optional[int]] = mapped_column(Integer)
    cantonal_rank: Mapped[Optional[int]] = mapped_column(Integer)

    scoring_version: Mapped[str] = mapped_column(String(20), default="v1")
    calculated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    municipality: Mapped["Municipality"] = relationship(back_populates="composite_scores")


from app.models.municipality import Municipality  # noqa: E402, F811
