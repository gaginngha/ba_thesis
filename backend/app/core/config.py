from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Swiss Municipality Analytics"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/swiss_municipalities"
    sync_database_url: str = "postgresql://postgres:postgres@localhost:5432/swiss_municipalities"

    # Data sources
    efv_base_url: str = "https://www.efv.admin.ch"
    bfs_pxweb_url: str = "https://www.pxweb.bfs.admin.ch/api/v1"
    opendata_swiss_url: str = "https://opendata.swiss/api/3"

    # Scoring weights (configurable)
    weight_financial: float = 0.30
    weight_tax: float = 0.20
    weight_demographic: float = 0.20
    weight_economic: float = 0.15
    weight_infrastructure: float = 0.15

    class Config:
        env_file = ".env"


settings = Settings()
