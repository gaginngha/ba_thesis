"""
Client for the opendata.swiss CKAN API.

Provides utilities to search and download datasets from the Swiss
Open Government Data portal.
"""

from typing import Optional

import httpx
from loguru import logger

OPENDATA_BASE = "https://opendata.swiss/api/3"


async def search_datasets(
    query: str,
    organization: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search for datasets on opendata.swiss.

    Args:
        query: Search term (e.g., "gemeindefinanzen")
        organization: Filter by organization (e.g., "bundesamt-fur-statistik-bfs")
        limit: Max results
    """
    params = {"q": query, "rows": limit}
    if organization:
        params["fq"] = f"organization:{organization}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{OPENDATA_BASE}/action/package_search", params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for dataset in data.get("result", {}).get("results", []):
        resources = []
        for res in dataset.get("resources", []):
            resources.append({
                "name": res.get("name", {}) if isinstance(res.get("name"), dict) else res.get("name", ""),
                "url": res.get("download_url") or res.get("url"),
                "format": res.get("format", "").upper(),
                "size": res.get("byte_size"),
            })

        results.append({
            "id": dataset["id"],
            "title": dataset.get("title", {}).get("de", dataset.get("title", "")),
            "description": dataset.get("description", {}).get("de", ""),
            "organization": dataset.get("organization", {}).get("name", ""),
            "resources": resources,
        })

    logger.info(f"Found {len(results)} datasets for query '{query}'")
    return results


async def get_dataset_resources(dataset_id: str) -> list[dict]:
    """Get all downloadable resources for a dataset."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{OPENDATA_BASE}/action/package_show",
            params={"id": dataset_id},
        )
        response.raise_for_status()
        data = response.json()

    dataset = data.get("result", {})
    resources = []
    for res in dataset.get("resources", []):
        url = res.get("download_url") or res.get("url")
        if url:
            resources.append({
                "name": res.get("name", ""),
                "url": url,
                "format": res.get("format", "").upper(),
            })

    return resources
