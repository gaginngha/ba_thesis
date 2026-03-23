"""
Natural language query endpoint.

Parses user queries like:
  "Show me municipalities in Aargau with population > 10000 and declining debt"
  "Top 10 most tax-attractive rural municipalities"
  "Compare Zürich and Bern financial health"

Uses rule-based NLP parsing to translate natural language into database queries.
"""

import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.municipality import Canton, Municipality
from app.models.financial import FinancialData
from app.models.demographic import DemographicData
from app.models.scores import CompositeScore

router = APIRouter()

# Canton name/abbreviation lookup
CANTON_ALIASES = {
    "zürich": "ZH", "zurich": "ZH", "zh": "ZH",
    "bern": "BE", "berne": "BE", "be": "BE",
    "luzern": "LU", "lucerne": "LU", "lu": "LU",
    "uri": "UR", "ur": "UR",
    "schwyz": "SZ", "sz": "SZ",
    "obwalden": "OW", "ow": "OW",
    "nidwalden": "NW", "nw": "NW",
    "glarus": "GL", "gl": "GL",
    "zug": "ZG", "zg": "ZG",
    "freiburg": "FR", "fribourg": "FR", "fr": "FR",
    "solothurn": "SO", "soleure": "SO", "so": "SO",
    "basel-stadt": "BS", "basel stadt": "BS", "bs": "BS",
    "basel-landschaft": "BL", "basel landschaft": "BL", "bl": "BL",
    "schaffhausen": "SH", "sh": "SH",
    "appenzell ausserrhoden": "AR", "ar": "AR",
    "appenzell innerrhoden": "AI", "ai": "AI",
    "st. gallen": "SG", "st gallen": "SG", "sg": "SG",
    "graubünden": "GR", "grisons": "GR", "gr": "GR",
    "aargau": "AG", "ag": "AG",
    "thurgau": "TG", "tg": "TG",
    "ticino": "TI", "tessin": "TI", "ti": "TI",
    "waadt": "VD", "vaud": "VD", "vd": "VD",
    "wallis": "VS", "valais": "VS", "vs": "VS",
    "neuenburg": "NE", "neuchâtel": "NE", "neuchatel": "NE", "ne": "NE",
    "genf": "GE", "genève": "GE", "geneva": "GE", "ge": "GE",
    "jura": "JU", "ju": "JU",
}

METRIC_ALIASES = {
    # Score metrics
    "score": "composite_score",
    "composite": "composite_score",
    "overall": "composite_score",
    "financial": "financial_health_score",
    "financial health": "financial_health_score",
    "tax": "tax_attractiveness_score",
    "tax attractiveness": "tax_attractiveness_score",
    "demographic": "demographic_vitality_score",
    "demographics": "demographic_vitality_score",
    "economic": "economic_strength_score",
    "economy": "economic_strength_score",
    # Financial metrics
    "debt": "net_debt_per_capita",
    "net debt": "net_debt_per_capita",
    "revenue": "revenue_per_capita",
    "expenditure": "expenditure_per_capita",
    "self-financing": "self_financing_ratio",
    "self financing": "self_financing_ratio",
    # Demographic metrics
    "population": "population_total",
    "growth": "population_growth_rate",
    "population growth": "population_growth_rate",
    "foreign": "foreign_share",
    "foreign share": "foreign_share",
    "dependency": "dependency_ratio",
}

PEER_GROUP_ALIASES = {
    "city": "city_large",
    "cities": "city_large",
    "large city": "city_large",
    "medium city": "city_medium",
    "urban": "urban",
    "suburban": "suburban",
    "rural": "rural_small",
    "small": "rural_small",
    "village": "rural_small",
}


def parse_query(query_text: str) -> dict:
    """
    Parse a natural language query into structured filters.
    """
    q = query_text.lower().strip()
    parsed = {
        "canton": None,
        "sort_metric": "composite_score",
        "sort_order": "desc",
        "limit": 20,
        "population_min": None,
        "population_max": None,
        "peer_group": None,
        "search_name": None,
        "filters": [],
    }

    # Extract canton
    for alias, abbr in CANTON_ALIASES.items():
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, q):
            parsed["canton"] = abbr
            break

    # Extract limit (e.g., "top 10", "top 5")
    limit_match = re.search(r"top\s+(\d+)", q)
    if limit_match:
        parsed["limit"] = min(int(limit_match.group(1)), 500)

    # Extract population thresholds
    pop_gt = re.search(r"population\s*(?:>|greater than|above|over|mehr als)\s*([\d,.']+)", q)
    if pop_gt:
        parsed["population_min"] = int(pop_gt.group(1).replace(",", "").replace("'", "").replace(".", ""))

    pop_lt = re.search(r"population\s*(?:<|less than|below|under|weniger als)\s*([\d,.']+)", q)
    if pop_lt:
        parsed["population_max"] = int(pop_lt.group(1).replace(",", "").replace("'", "").replace(".", ""))

    # Extract sort metric
    for alias, metric in METRIC_ALIASES.items():
        if alias in q:
            parsed["sort_metric"] = metric
            break

    # Detect sort direction
    if any(word in q for word in ["lowest", "least", "worst", "bottom", "tiefste", "niedrigste"]):
        parsed["sort_order"] = "asc"
    if any(word in q for word in ["highest", "best", "top", "most", "höchste"]):
        parsed["sort_order"] = "desc"

    # Extract peer group
    for alias, pg in PEER_GROUP_ALIASES.items():
        if alias in q:
            parsed["peer_group"] = pg
            break

    # Extract municipality name search
    name_match = re.search(r"(?:named?|called)\s+['\"]?(\w+)['\"]?", q)
    if name_match:
        parsed["search_name"] = name_match.group(1)

    return parsed


@router.get("/")
async def natural_language_query(
    q: str = Query(..., description="Natural language query", min_length=3),
    db: AsyncSession = Depends(get_db),
):
    """
    Query municipalities using natural language.

    Examples:
    - "Top 10 municipalities in Zürich by financial health"
    - "Municipalities with population over 20000 sorted by tax attractiveness"
    - "Best rural municipalities by composite score"
    - "Bottom 5 municipalities by debt in Bern"
    """
    parsed = parse_query(q)

    # Determine source table based on metric
    score_metrics = {
        "composite_score", "financial_health_score", "tax_attractiveness_score",
        "demographic_vitality_score", "economic_strength_score",
    }
    financial_metrics = {
        "net_debt_per_capita", "revenue_per_capita", "expenditure_per_capita",
        "self_financing_ratio", "tax_revenue_per_capita",
    }
    demographic_metrics = {
        "population_total", "population_growth_rate", "foreign_share", "dependency_ratio",
    }

    metric = parsed["sort_metric"]

    # Build the query dynamically
    if metric in score_metrics:
        sort_col = getattr(CompositeScore, metric)
        query = (
            select(
                Municipality.bfs_number,
                Municipality.name,
                Canton.abbreviation.label("canton"),
                Municipality.population,
                sort_col.label("metric_value"),
                CompositeScore.peer_group,
                CompositeScore.year,
            )
            .join(Canton, Municipality.canton_id == Canton.id)
            .join(CompositeScore, CompositeScore.municipality_bfs == Municipality.bfs_number)
            .where(Municipality.is_active.is_(True))
        )
    elif metric in financial_metrics:
        sort_col = getattr(FinancialData, metric)
        query = (
            select(
                Municipality.bfs_number,
                Municipality.name,
                Canton.abbreviation.label("canton"),
                Municipality.population,
                sort_col.label("metric_value"),
                FinancialData.year,
            )
            .join(Canton, Municipality.canton_id == Canton.id)
            .join(FinancialData, FinancialData.municipality_bfs == Municipality.bfs_number)
            .where(Municipality.is_active.is_(True))
        )
    elif metric in demographic_metrics:
        sort_col = getattr(DemographicData, metric)
        query = (
            select(
                Municipality.bfs_number,
                Municipality.name,
                Canton.abbreviation.label("canton"),
                Municipality.population,
                sort_col.label("metric_value"),
                DemographicData.year,
            )
            .join(Canton, Municipality.canton_id == Canton.id)
            .join(DemographicData, DemographicData.municipality_bfs == Municipality.bfs_number)
            .where(Municipality.is_active.is_(True))
        )
    else:
        return {"error": f"Unknown metric: {metric}", "parsed": parsed}

    # Apply filters
    if parsed["canton"]:
        query = query.where(Canton.abbreviation == parsed["canton"])
    if parsed["population_min"]:
        query = query.where(Municipality.population >= parsed["population_min"])
    if parsed["population_max"]:
        query = query.where(Municipality.population <= parsed["population_max"])
    if parsed["peer_group"] and metric in score_metrics:
        query = query.where(CompositeScore.peer_group == parsed["peer_group"])
    if parsed["search_name"]:
        query = query.where(Municipality.name.ilike(f"%{parsed['search_name']}%"))

    # Sort
    if parsed["sort_order"] == "desc":
        query = query.order_by(sort_col.desc().nulls_last())
    else:
        query = query.order_by(sort_col.asc().nulls_last())

    query = query.limit(parsed["limit"])

    result = await db.execute(query)
    rows = result.all()

    return {
        "query": q,
        "parsed": parsed,
        "count": len(rows),
        "results": [
            {
                "bfs_number": row.bfs_number,
                "name": row.name,
                "canton": row.canton,
                "population": row.population,
                "metric": metric,
                "value": float(row.metric_value) if row.metric_value is not None else None,
                "year": row.year,
            }
            for row in rows
        ],
    }
