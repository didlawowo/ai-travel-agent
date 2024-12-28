import os
from typing import Optional
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
import serpapi
from loguru import logger


class FlightsInput(BaseModel):
    departure_airport: str = Field(description="Departure airport code (IATA)")
    arrival_airport: str = Field(description="Arrival airport code (IATA)")
    outbound_date: str = Field(description="Outbound date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(
        None, description="Return date in YYYY-MM-DD format"
    )
    currency: Optional[str] = Field("EUR", description="Currency for prices")
    adults: Optional[int] = Field(1, description="Number of adult passengers")
    children: Optional[int] = Field(0, description="Number of child passengers")
    infants_in_seat: Optional[int] = Field(0, description="Number of infants in seat")
    infants_on_lap: Optional[int] = Field(0, description="Number of infants on lap")
    travel_class: Optional[int] = Field(
        1, description="Travel class (1=Economy, 2=Business, 3=First)"
    )


class FlightsInputSchema(BaseModel):
    params: FlightsInput


@tool(args_schema=FlightsInputSchema)
def flights_finder(params: FlightsInput):
    """Find flights using the Google Flights engine."""

    logger.info(f"🔍 Starting flight search with parameters: {params}")

    # Erreur 1 corrigée: departure_id -> departure_airport
    search_params = {
        "api_key": os.environ.get("SERPAPI_API_KEY"),
        "engine": "google_flights",
        "hl": "fr",
        "gl": "fr",
        "type": "2",  # Aller simple par défaut
        "departure_id": params.departure_airport,
        "arrival_id": params.arrival_airport,
        "outbound_date": params.outbound_date,
        "currency": params.currency,
        "adults": params.adults,
        "travel_class": 1,
        "deep_search": True,
        "stops": 1,
    }

    if params.children and params.children > 0:
        search_params["children"] = str(params.children)
    if params.infants_in_seat and params.infants_in_seat > 0:
        search_params["infants_in_seat"] = str(params.infants_in_seat)
    if params.infants_on_lap and params.infants_on_lap > 0:
        search_params["infants_on_lap"] = str(params.infants_on_lap)

    # Erreur 3 corrigée: Gestion du vol aller-retour
    if params.return_date:
        search_params["type"] = "1"  # Changement en aller-retour
        search_params["return_date"] = params.return_date

    logger.info(f"🌐 Prepared SerpAPI parameters: {search_params}")

    try:
        # Erreur 4 corrigée: Appel à serpapi.search
        logger.info("🚀 Making API call to SerpAPI")
        search = serpapi.search(params=search_params)  # Correction ici
        logger.info("✅ API call successful")

        if search.data:
            logger.info(f"📝 Response keys: {search.data.values()}")
            flights = search.data.get("flights", search.data.get("best_flights", []))
            return {
                "status": "success",
                "flights": flights,
                "count": len(flights) if flights else 0,
                "search_params": search_params,
            }
        else:
            return {
                "status": "no_data",
                "message": "No data returned from search",
                "search_params": search_params,
            }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error in flight search: {error_msg}")
        logger.error(f"Parameters used: {search_params}")
        return {"status": "error", "message": error_msg, "parameters": search_params}
