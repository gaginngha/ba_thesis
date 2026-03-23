"""
ETL pipeline for EFV (Federal Finance Administration) data.

Downloads and processes municipality financial data from:
- opendata.swiss public finance datasets
- EFV financial statistics (Finanzstatistik)
"""

import io
from pathlib import Path

import httpx
import pandas as pd
from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Known EFV / opendata.swiss dataset URLs for municipality finances
EFV_DATASETS = {
    # Öffentliche Finanzen – Statistik der Schweizer Städte
    "public_finances": "https://dam-api.bfs.admin.ch/hub/api/dam/assets/32007693/master",
    # Finanzstatistik – Kennzahlen der Gemeinden (FS model)
    "fs_indicators": "https://www.efv.admin.ch/dam/efv/de/dokumente/finanzstatistik/daten/kennzahlen_gemeinden.xlsx.download.xlsx/kennzahlen_gemeinden.xlsx",
    # Finanzstatistik – Gemeindefinanzen Detaildaten
    "fs_detail": "https://www.efv.admin.ch/dam/efv/de/dokumente/finanzstatistik/daten/oeffentliche_finanzen_gemeinden.xlsx.download.xlsx/gemeinden.xlsx",
}

# Kanton Zürich specific (rich HRM2 data on opendata.swiss)
ZH_DATASETS = {
    "finanzvermogen": "https://www.web.statistik.zh.ch/ogd/data/KANTON_ZUERICH_267.csv",
    "nettoschuld": "https://www.web.statistik.zh.ch/ogd/data/KANTON_ZUERICH_268.csv",
    "steuerfuss": "https://www.web.statistik.zh.ch/ogd/data/KANTON_ZUERICH_265.csv",
    "selbstfinanzierung": "https://www.web.statistik.zh.ch/ogd/data/KANTON_ZUERICH_269.csv",
}


async def download_file(url: str, filename: str) -> Path:
    """Download a file from a URL and save to data/raw/."""
    raw_dir = DATA_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    filepath = raw_dir / filename

    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        logger.info(f"Downloading {url} -> {filepath}")
        response = await client.get(url)
        response.raise_for_status()
        filepath.write_bytes(response.content)

    logger.info(f"Downloaded {filepath} ({filepath.stat().st_size / 1024:.1f} KB)")
    return filepath


def parse_efv_indicators(filepath: Path) -> pd.DataFrame:
    """Parse EFV municipality financial indicators Excel file."""
    logger.info(f"Parsing EFV indicators from {filepath}")

    df = pd.read_excel(filepath, sheet_name=0, header=0)

    # Common column mapping (EFV uses German headers)
    column_map = {
        "BFS-Nr.": "municipality_bfs",
        "BFS_NR": "municipality_bfs",
        "Gemeinde-Nr.": "municipality_bfs",
        "Jahr": "year",
        "Gesamtertrag": "total_revenue",
        "Steuerertrag": "tax_revenue",
        "Gesamtaufwand": "total_expenditure",
        "Personalaufwand": "personnel_expenditure",
        "Ergebnis Erfolgsrechnung": "operating_result",
        "Nettoschuld": "net_debt",
        "Nettoschuld pro Kopf": "net_debt_per_capita",
        "Eigenkapital": "equity",
        "Selbstfinanzierungsgrad": "self_financing_ratio",
        "Selbstfinanzierung": "self_financing_capacity",
        "Verschuldungsgrad": "debt_ratio",
        "Zinsbelastungsanteil": "interest_burden_ratio",
        "Investitionsanteil": "investment_ratio",
        "Kapitaldienstanteil": "capital_service_ratio",
        "Nettoverschuldungsquotient": "net_debt_quota",
    }

    # Rename columns that exist
    rename = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Ensure required columns exist
    if "municipality_bfs" not in df.columns or "year" not in df.columns:
        logger.warning("Could not find BFS number or year columns. Available: {}", list(df.columns))
        return pd.DataFrame()

    df["municipality_bfs"] = pd.to_numeric(df["municipality_bfs"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["municipality_bfs", "year"])
    df["municipality_bfs"] = df["municipality_bfs"].astype(int)
    df["year"] = df["year"].astype(int)
    df["data_source"] = "efv"

    logger.info(f"Parsed {len(df)} records, years {df['year'].min()}-{df['year'].max()}")
    return df


def parse_zh_csv(filepath: Path, metric_name: str) -> pd.DataFrame:
    """Parse Kanton Zürich statistical CSV files."""
    logger.info(f"Parsing ZH CSV: {filepath} (metric: {metric_name})")

    df = pd.read_csv(filepath)

    # ZH CSVs typically have: BFS_NR, GEBIET_NAME, INDIKATOR_JAHR, INDIKATOR_VALUE
    col_map = {
        "BFS_NR": "municipality_bfs",
        "INDIKATOR_JAHR": "year",
        "INDIKATOR_VALUE": metric_name,
    }
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "municipality_bfs" in df.columns and "year" in df.columns:
        df = df[["municipality_bfs", "year", metric_name]].dropna()
        df["municipality_bfs"] = df["municipality_bfs"].astype(int)
        df["year"] = df["year"].astype(int)

    return df


def load_financial_data_to_db(df: pd.DataFrame, db_url: str):
    """Load processed financial data into PostgreSQL."""
    from sqlalchemy import create_engine

    engine = create_engine(db_url)

    # Map DataFrame columns to DB columns
    db_columns = [
        "municipality_bfs", "year", "total_revenue", "tax_revenue",
        "total_expenditure", "personnel_expenditure", "operating_result",
        "total_assets", "financial_assets", "total_liabilities",
        "net_debt", "equity", "revenue_per_capita", "expenditure_per_capita",
        "net_debt_per_capita", "tax_revenue_per_capita",
        "self_financing_ratio", "self_financing_capacity", "debt_ratio",
        "interest_burden_ratio", "investment_ratio", "capital_service_ratio",
        "net_debt_quota", "data_source", "accounting_standard",
    ]
    available = [c for c in db_columns if c in df.columns]
    df_insert = df[available].copy()

    with engine.begin() as conn:
        # Upsert: delete existing records for same municipality/year/source, then insert
        for _, row in df_insert.iterrows():
            conn.execute(
                text(
                    "DELETE FROM financial_data WHERE municipality_bfs = :bfs AND year = :yr AND data_source = :src"
                ),
                {"bfs": int(row["municipality_bfs"]), "yr": int(row["year"]), "src": row.get("data_source", "efv")},
            )

        df_insert.to_sql("financial_data", conn, if_exists="append", index=False, method="multi")

    logger.info(f"Loaded {len(df_insert)} financial records into database")


async def run_efv_pipeline(db_url: str):
    """Main ETL pipeline for EFV financial data."""
    logger.info("Starting EFV financial data ETL pipeline")

    # 1. Download EFV indicators
    try:
        filepath = await download_file(
            EFV_DATASETS["fs_indicators"],
            "efv_kennzahlen_gemeinden.xlsx",
        )
        df = parse_efv_indicators(filepath)
        if not df.empty:
            load_financial_data_to_db(df, db_url)
    except Exception as e:
        logger.error(f"Failed to process EFV indicators: {e}")

    # 2. Download Kanton Zürich detailed data
    zh_metric_map = {
        "finanzvermogen": "financial_assets",
        "nettoschuld": "net_debt",
        "steuerfuss": "tax_multiplier",
        "selbstfinanzierung": "self_financing_capacity",
    }
    zh_frames = []
    for key, metric in zh_metric_map.items():
        try:
            filepath = await download_file(ZH_DATASETS[key], f"zh_{key}.csv")
            df = parse_zh_csv(filepath, metric)
            if not df.empty:
                zh_frames.append(df)
        except Exception as e:
            logger.warning(f"Failed to download ZH {key}: {e}")

    if zh_frames:
        # Merge all ZH metrics on municipality_bfs + year
        zh_merged = zh_frames[0]
        for frame in zh_frames[1:]:
            zh_merged = zh_merged.merge(frame, on=["municipality_bfs", "year"], how="outer")
        zh_merged["data_source"] = "zh_statistik"
        load_financial_data_to_db(zh_merged, db_url)

    logger.info("EFV ETL pipeline complete")
