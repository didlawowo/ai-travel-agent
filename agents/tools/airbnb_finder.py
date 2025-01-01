import os
from typing import Optional, List
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
from loguru import logger
import requests  # 🌐 Pour les appels API Airbnb


class AirbnbInput(BaseModel):
    location: str = Field(description="Location for the search")
    check_in: str = Field(description="Check-in date in YYYY-MM-DD format")
    check_out: str = Field(description="Check-out date in YYYY-MM-DD format")
    currency: Optional[str] = Field("EUR", description="Currency for prices")
    adults: Optional[int] = Field(1, description="Number of adults")
    children: Optional[int] = Field(0, description="Number of children")
    min_price: Optional[int] = Field(None, description="Minimum price per night")
    max_price: Optional[int] = Field(None, description="Maximum price per night")
    room_types: Optional[List[str]] = Field(
        None,
        description="Type of accommodation (Entire home, Private room, Shared room)",
    )
    amenities: Optional[List[str]] = Field(None, description="Required amenities")
    sort_by: Optional[str] = Field(
        "rating",
        description="""Sorting options:
        price_low: Price (low to high)
        price_high: Price (high to low)
        rating: Best rating (default)
        """,
    )


class AirbnbInputSchema(BaseModel):
    params: AirbnbInput


@tool(args_schema=AirbnbInputSchema)
def airbnb_finder(params: AirbnbInput):
    """
    🏠 Find accommodations using Airbnb with advanced filtering
    """
    logger.info(f"🔍 Starting Airbnb search for location: {params.location}")
    logger.info(f"📅 Dates: {params.check_in} to {params.check_out}")

    # 🔑 Configuration de l'authentification Airbnb
    headers = {
        "X-Airbnb-API-Key": os.environ.get("AIRBNB_API_KEY"),
        "Accept": "application/json",
    }

    # 🛠️ Construction des paramètres de recherche
    search_params = {
        "query": params.location,
        "check_in": params.check_in,
        "check_out": params.check_out,
        "adults": params.adults,
        "children": params.children,
        "currency": params.currency,
        "sort": params.sort_by,
    }

    # 💰 Ajout des filtres de prix
    if params.min_price:
        search_params["price_min"] = params.min_price
    if params.max_price:
        search_params["price_max"] = params.max_price

    # 🏘️ Ajout des types de logement
    if params.room_types:
        search_params["room_types"] = ",".join(params.room_types)

    try:
        # 🌐 Appel à l'API Airbnb
        response = requests.get(
            "https://api.airbnb.com/v2/search_results",
            headers=headers,
            params=search_params,
        )
        data = response.json()

        if not data or "listings" not in data:
            logger.warning("⚠️ No accommodations found")
            return {
                "status": "no_results",
                "message": "No accommodations found for these criteria",
                "search_params": search_params,
            }

        # ✨ Traitement des résultats
        listings = data["listings"]
        if params.amenities:
            listings = filter_listings_by_amenities(listings, params.amenities)

        return {
            "status": "success",
            "accommodations": format_listings(listings[:5]),  # 🔄 Limite à 5 résultats
            "total_found": len(listings),
            "search_parameters": {
                "location": params.location,
                "dates": {"check_in": params.check_in, "check_out": params.check_out},
                "guests": {"adults": params.adults, "children": params.children},
                "currency": params.currency,
            },
        }

    except Exception as e:
        logger.error(f"❌ Error in Airbnb search: {str(e)}")
        return {"status": "error", "message": str(e), "parameters": search_params}


def filter_listings_by_amenities(listings: list, required_amenities: List[str]) -> list:
    """
    🎯 Filter listings by required amenities
    """
    filtered = []
    for listing in listings:
        amenities = listing.get("amenities", [])
        if all(
            amenity.lower() in [a.lower() for a in amenities]
            for amenity in required_amenities
        ):
            filtered.append(listing)
    return filtered


def format_listings(listings: list) -> list:
    """
    🏡 Format listing data for better readability
    """
    formatted = []
    for listing in listings:
        formatted.append(
            {
                "id": listing.get("id"),
                "title": listing.get("name"),
                "type": listing.get("room_type"),
                "price": listing.get("price"),
                "rating": listing.get("rating"),
                "reviews": listing.get("reviews_count"),
                "location": {
                    "neighborhood": listing.get("neighborhood"),
                    "city": listing.get("city"),
                },
                "amenities": listing.get("amenities", []),
            }
        )
    return formatted
