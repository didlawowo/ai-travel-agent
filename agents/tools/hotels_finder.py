import os
from typing import Optional, List
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
import serpapi
from loguru import logger


class HotelsInput(BaseModel):
    q: str = Field(description="Location of the hotel")
    check_in_date: str = Field(description="Check-in date in YYYY-MM-DD format")
    check_out_date: str = Field(description="Check-out date in YYYY-MM-DD format")
    currency: Optional[str] = Field("EUR", description="Currency for prices")
    adults: Optional[int] = Field(1, description="Number of adults")
    children: Optional[int] = Field(0, description="Number of children")
    rooms: Optional[int] = Field(1, description="Number of rooms")
    hotel_class: Optional[str] = Field(None, description="Hotel class (2,3,4,5)")
    sort_by: Optional[str] = Field(
        "8",
        description="""Sorting options:
        1: Price (low to high)
        2: Price (high to low)
        3: Distance
        8: Rating (default)
        """,
    )
    min_price: Optional[int] = Field(None, description="Minimum price per night")
    max_price: Optional[int] = Field(None, description="Maximum price per night")
    amenities: Optional[List[str]] = Field(None, description="Required amenities")


class HotelsInputSchema(BaseModel):
    params: HotelsInput


@tool(args_schema=HotelsInputSchema)
def hotels_finder(params: HotelsInput):
    """
    🏨 Find hotels using the Google Hotels engine with advanced filtering.
    """
    logger.info(f"🔍 Starting hotel search for location: {params.q}")
    logger.info(f"📅 Dates: {params.check_in_date} to {params.check_out_date}")

    # Construction des paramètres de base
    search_params = {
        "api_key": os.environ.get("SERPAPI_API_KEY"),
        "engine": "google_hotels",
        "hl": "fr",
        "gl": "fr",
        "q": params.q,
        "check_in_date": params.check_in_date,
        "check_out_date": params.check_out_date,
        "currency": params.currency,
        "sort_by": str(params.sort_by),
    }

    # Ajout des paramètres optionnels
    if params.adults:
        search_params["adults"] = str(params.adults)
    if params.children:
        search_params["children"] = str(params.children)
    if params.rooms:
        search_params["rooms"] = str(params.rooms)
    if params.hotel_class:
        search_params["hotel_class"] = params.hotel_class
    if params.min_price:
        search_params["min_price"] = str(params.min_price)
    if params.max_price:
        search_params["max_price"] = str(params.max_price)

    logger.info(f"🌐 Prepared search parameters: {search_params}")

    try:
        logger.info("🚀 Making API call to SerpAPI")
        search = serpapi.search(params=search_params)
        logger.info("✅ API call successful")

        if not search.data or "properties" not in search.data:
            logger.warning("⚠️ No hotels found")
            return {
                "status": "no_results",
                "message": "No hotels found for these criteria",
                "search_params": search_params,
            }

        # Récupération et traitement des résultats
        hotels = search.data["properties"]
        logger.info(f"✨ Found {len(hotels)} hotels")

        # Application des filtres supplémentaires
        if params.amenities:
            hotels = filter_hotels_by_amenities(hotels, params.amenities)

        # Préparation de la réponse
        response = {
            "status": "success",
            "hotels": hotels[:5],  # Limitation à 5 résultats
            "total_found": len(hotels),
            "search_parameters": {
                "location": params.q,
                "dates": {
                    "check_in": params.check_in_date,
                    "check_out": params.check_out_date,
                },
                "guests": {"adults": params.adults, "children": params.children},
                "rooms": params.rooms,
                "hotel_class": params.hotel_class,
                "currency": params.currency,
            },
        }

        return response

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error in hotel search: {error_msg}")
        logger.error(f"Parameters used: {search_params}")
        return {"status": "error", "message": error_msg, "parameters": search_params}


def filter_hotels_by_amenities(hotels: list, required_amenities: List[str]) -> list:
    """
    🎯 Filtre les hôtels selon les équipements requis
    """
    filtered = []
    for hotel in hotels:
        amenities = hotel.get("amenities", [])
        if all(
            amenity.lower() in [a.lower() for a in amenities]
            for amenity in required_amenities
        ):
            filtered.append(hotel)
    return filtered


def format_hotel_price(price: str, currency: str) -> str:
    """
    💰 Formate le prix de l'hôtel
    """
    if not price:
        return "Prix non disponible"
    try:
        # Suppression des caractères non numériques sauf le point
        numeric_price = "".join(c for c in price if c.isdigit() or c == ".")
        price_float = float(numeric_price)
        return f"{price_float:.2f} {currency}"
    except Exception as e:
        logger.warn(f"Error formatting hotel price: {e}")
        return price
