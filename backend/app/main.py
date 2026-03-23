from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    municipalities, financial, demographics, scores,
    trends, benchmark, geodata, reports, nlquery,
)
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Analytics platform for Swiss municipalities — financial, demographic, and economic data",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(municipalities.router, prefix="/api/v1/municipalities", tags=["Municipalities"])
app.include_router(financial.router, prefix="/api/v1/financial", tags=["Financial Data"])
app.include_router(demographics.router, prefix="/api/v1/demographics", tags=["Demographics"])
app.include_router(scores.router, prefix="/api/v1/scores", tags=["Composite Scores"])
app.include_router(trends.router, prefix="/api/v1/trends", tags=["Trends & Forecasting"])
app.include_router(benchmark.router, prefix="/api/v1/benchmark", tags=["Benchmarking"])
app.include_router(geodata.router, prefix="/api/v1/geo", tags=["Geodata"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(nlquery.router, prefix="/api/v1/query", tags=["Natural Language Query"])


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}
