import os
from typing import Optional, List, Tuple, Literal
from dotenv import load_dotenv
import httpx

# Загрузка переменных окружения
load_dotenv(override=True)

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
if not MAPBOX_TOKEN:
    raise ValueError("MAPBOX_TOKEN is not set in .env")

MAPBOX_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"


async def _query_mapbox(
    query: str,
    limit: int = 5,
    autocomplete: bool = True,
    language: Literal["ru", "en"] = "ru"
) -> List[dict]:
    params = {
        "access_token": MAPBOX_TOKEN,
        "autocomplete": str(autocomplete).lower(),
        "limit": limit,
        "language": language
    }
    url = f"{MAPBOX_URL}/{query}.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("features", [])
        return []


async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    features = await _query_mapbox(address, limit=1, autocomplete=False)
    if features:
        lon, lat = features[0]["center"]
        return lat, lon
    return None


async def autocomplete_address(query: str) -> List[dict]:
    features = await _query_mapbox(query, limit=3, autocomplete=True)
    return [
        {
            "label": f["place_name"],
            "lat": f["center"][1],
            "lon": f["center"][0]
        }
        for f in features
    ]

