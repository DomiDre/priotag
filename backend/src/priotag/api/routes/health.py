"""Health check endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    status_code=200,
    summary="Health Check",
    description="Check if the API is running and healthy",
)
async def health_check():
    """Health check endpoint."""
    return


@router.get(
    "/build-info",
    status_code=200,
    summary="Build Information",
    description="Get build and version information for verification",
)
async def build_info():
    """Return build information for transparency and verification."""
    build_info_file = Path("/app/build_info.json")

    # Default fallback if file doesn't exist (development mode)
    default_info = {
        "version": "development",
        "commit": "unknown",
        "build_date": "unknown",
        "source_url": "https://github.com/DomiDre/priotag",
    }

    if build_info_file.exists():
        try:
            with open(build_info_file, "r") as f:
                return json.load(f)
        except Exception:
            return default_info

    return default_info
