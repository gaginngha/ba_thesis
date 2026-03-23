from pydantic import BaseModel
from typing import Optional


class CantonResponse(BaseModel):
    bfs_number: int
    abbreviation: str
    name_de: str
    name_fr: Optional[str] = None

    model_config = {"from_attributes": True}


class MunicipalityListItem(BaseModel):
    bfs_number: int
    name: str
    canton_abbreviation: str
    population: Optional[int] = None
    municipality_type: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class MunicipalityDetail(BaseModel):
    bfs_number: int
    name: str
    canton: CantonResponse
    population: Optional[int] = None
    area_km2: Optional[float] = None
    altitude_m: Optional[int] = None
    municipality_type: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class FinancialDataResponse(BaseModel):
    municipality_bfs: int
    year: int
    total_revenue: Optional[float] = None
    tax_revenue: Optional[float] = None
    total_expenditure: Optional[float] = None
    operating_result: Optional[float] = None
    net_debt: Optional[float] = None
    equity: Optional[float] = None
    revenue_per_capita: Optional[float] = None
    expenditure_per_capita: Optional[float] = None
    net_debt_per_capita: Optional[float] = None
    self_financing_ratio: Optional[float] = None
    debt_ratio: Optional[float] = None
    data_source: str = "efv"

    model_config = {"from_attributes": True}


class DemographicResponse(BaseModel):
    municipality_bfs: int
    year: int
    population_total: Optional[int] = None
    population_swiss: Optional[int] = None
    population_foreign: Optional[int] = None
    foreign_share: Optional[float] = None
    age_0_19: Optional[int] = None
    age_20_39: Optional[int] = None
    age_40_64: Optional[int] = None
    age_65_plus: Optional[int] = None
    dependency_ratio: Optional[float] = None
    births: Optional[int] = None
    deaths: Optional[int] = None
    net_migration: Optional[int] = None
    population_growth_rate: Optional[float] = None

    model_config = {"from_attributes": True}


class CompositeScoreResponse(BaseModel):
    municipality_bfs: int
    municipality_name: Optional[str] = None
    canton_abbreviation: Optional[str] = None
    year: int
    financial_health_score: Optional[float] = None
    tax_attractiveness_score: Optional[float] = None
    demographic_vitality_score: Optional[float] = None
    economic_strength_score: Optional[float] = None
    composite_score: Optional[float] = None
    peer_group: Optional[str] = None
    peer_group_rank: Optional[int] = None
    national_rank: Optional[int] = None
    cantonal_rank: Optional[int] = None

    model_config = {"from_attributes": True}


class TimeSeriesPoint(BaseModel):
    year: int
    value: Optional[float] = None


class MunicipalityComparison(BaseModel):
    bfs_number: int
    name: str
    canton: str
    scores: Optional[CompositeScoreResponse] = None
    financials: Optional[FinancialDataResponse] = None
    demographics: Optional[DemographicResponse] = None
