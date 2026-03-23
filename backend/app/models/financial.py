from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FinancialData(Base):
    __tablename__ = "financial_data"
    __table_args__ = (
        UniqueConstraint("municipality_bfs", "year", "data_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_bfs: Mapped[int] = mapped_column(
        Integer, ForeignKey("municipalities.bfs_number"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)

    # Revenue
    total_revenue: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    tax_revenue: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    fiscal_equalization: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))

    # Expenditure
    total_expenditure: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    personnel_expenditure: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))

    # Balance
    operating_result: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))

    # Balance sheet
    total_assets: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    financial_assets: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    total_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    net_debt: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    equity: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))

    # Per capita
    revenue_per_capita: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    expenditure_per_capita: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    net_debt_per_capita: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    tax_revenue_per_capita: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    # HRM2 indicators
    self_financing_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    self_financing_capacity: Mapped[Optional[float]] = mapped_column(Numeric(15, 2))
    debt_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    interest_burden_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    investment_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    capital_service_ratio: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))
    net_debt_quota: Mapped[Optional[float]] = mapped_column(Numeric(8, 4))

    # Metadata
    data_source: Mapped[str] = mapped_column(String(50), default="efv")
    accounting_standard: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    municipality: Mapped["Municipality"] = relationship(back_populates="financial_data")


class TaxData(Base):
    __tablename__ = "tax_data"
    __table_args__ = (
        UniqueConstraint("municipality_bfs", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    municipality_bfs: Mapped[int] = mapped_column(
        Integer, ForeignKey("municipalities.bfs_number"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    tax_multiplier: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    income_tax_index: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    wealth_tax_index: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    corporate_tax_index: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    tax_revenue_per_capita: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))

    data_source: Mapped[str] = mapped_column(String(50), default="efv")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# Avoid circular import
from app.models.municipality import Municipality  # noqa: E402, F811
