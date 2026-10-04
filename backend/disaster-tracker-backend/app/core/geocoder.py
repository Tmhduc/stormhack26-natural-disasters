"""Optional reverse geocoding for inspected coordinates."""

from functools import lru_cache

import requests

from app.config import GOOGLE_MAPS_API_KEY


@lru_cache(maxsize=256)
def _reverse_geocode_cached(lat: float, lon: float) -> str | None:
    if not GOOGLE_MAPS_API_KEY:
        return None
    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={
                "latlng": f"{lat},{lon}",
                "key": GOOGLE_MAPS_API_KEY,
                "language": "vi",
                "region": "vn",
            },
            timeout=5,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0].get("formatted_address") if results else None
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return None


def reverse_geocode(lat: float, lon: float) -> str | None:
    """Return a localized address, if Google geocoding is configured."""
    # Avoid duplicate calls for tiny coordinate differences from map clicks.
    return _reverse_geocode_cached(round(lat, 5), round(lon, 5))


@lru_cache(maxsize=128)
def _forward_geocode_cached(query: str) -> tuple[dict, ...]:
    if not GOOGLE_MAPS_API_KEY:
        return ()
    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={
                "address": query,
                "key": GOOGLE_MAPS_API_KEY,
                "language": "vi",
                "region": "vn",
            },
            timeout=5,
        )
        response.raise_for_status()
        return tuple(
            {
                "address": item.get("formatted_address", query),
                "lat": item["geometry"]["location"]["lat"],
                "lon": item["geometry"]["location"]["lng"],
            }
            for item in response.json().get("results", [])[:5]
        )
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return ()


def forward_geocode(query: str) -> list[dict]:
    """Find up to five Vietnamese address matches for a search query."""
    return list(_forward_geocode_cached(" ".join(query.split())[:200]))
