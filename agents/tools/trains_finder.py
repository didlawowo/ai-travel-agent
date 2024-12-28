import os
from typing import Optional
from datetime import datetime
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
import requests
from loguru import logger


class TrainsInput(BaseModel):
    origin_city: str = Field(description="Ville de départ (ex: Paris)")
    destination_city: str = Field(description="Ville d'arrivée (ex: Lyon)")
    departure_date: str = Field(description="Date de départ (YYYY-MM-DD)")
    departure_time: Optional[str] = Field(None, description="Heure de départ (HH:MM)")


class TrainsInputSchema(BaseModel):
    params: TrainsInput


def parse_fare_info(fare_data: dict) -> dict:
    """
    Analyse les informations de tarif depuis la réponse de l'API
    """
    if not fare_data or not fare_data.get("found"):
        return {"found": False, "total": "N/A", "currency": "EUR", "tickets": []}

    tickets = []
    for ticket in fare_data.get("links", []):
        if "ticket" in ticket.get("id", ""):
            ticket_info = {
                "id": ticket.get("id"),
                "name": ticket.get("name", "N/A"),
                "cost": ticket.get("cost", {}).get("value", "N/A"),
                "currency": ticket.get("cost", {}).get("currency", "EUR"),
            }
            tickets.append(ticket_info)

    return {
        "found": True,
        "total": fare_data.get("total", {}).get("value", "N/A"),
        "currency": fare_data.get("total", {}).get("currency", "EUR"),
        "tickets": tickets,
    }


def format_datetime(date: str, time: str = None) -> str:
    """Formate la date et l'heure pour l'API SNCF"""
    if time:
        return f"{date.replace('-', '')}T{time.replace(':', '')}00"
    return f"{date.replace('-', '')}T000000"


@tool(args_schema=TrainsInputSchema)
def trains_finder(params: TrainsInput):
    """
    🚂 Recherche des trains SNCF
    """
    logger.info(
        f"🔍 Starting train search: {params.origin_city} → {params.destination_city}"
    )

    # Configuration de l'API SNCF
    SNCF_API_KEY = os.environ.get("SNCF_API_KEY")
    base_url = "https://api.sncf.com/v1/coverage/sncf/journeys"

    # Préparation de la date/heure
    datetime_str = format_datetime(params.departure_date, params.departure_time)

    # Paramètres de recherche
    search_params = {
        "from": f"admin:fr:{params.origin_city}",
        "to": f"admin:fr:{params.destination_city}",
        "datetime": datetime_str,
        "datetime_represents": "departure",
        "equipment_details": True,  # Pour avoir plus de détails
        "data_freshness": "realtime",  # Pour avoir les prix en temps réel
        # "count": 5,  # Limiter à 5 résultats
    }

    try:
        logger.info("🚀 Making API call to SNCF")
        response = requests.get(base_url, params=search_params, auth=(SNCF_API_KEY, ""))

        if response.status_code != 200:
            logger.error(f"❌ API error: {response.status_code}")
            return {
                "status": "error",
                "message": f"API error: {response.status_code}",
                "parameters": search_params,
            }

        data = response.json()
        journeys = data.get("journeys", [])

        # Traitement des résultats
        trains = []
        for journey in journeys:
            transport_sections = [
                section
                for section in journey["sections"]
                if section.get("type") == "public_transport"
            ]

            if transport_sections:
                section = transport_sections[0]
                display_info = section.get("display_informations", {})

                # Formatage des dates
                departure_time = datetime.strptime(
                    journey["departure_date_time"], "%Y%m%dT%H%M%S"
                )
                arrival_time = datetime.strptime(
                    journey["arrival_date_time"], "%Y%m%dT%H%M%S"
                )

                train = {
                    "departure": {
                        "station": section["from"]["stop_point"]["name"],
                        "city": section["from"]["stop_point"]["label"],
                        "time": departure_time.strftime("%H:%M"),
                    },
                    "arrival": {
                        "station": section["to"]["stop_point"]["name"],
                        "city": section["to"]["stop_point"]["label"],
                        "time": arrival_time.strftime("%H:%M"),
                    },
                    "duration_minutes": journey["duration"] // 60,
                    "train_type": display_info.get("commercial_mode", ""),
                    "train_number": display_info.get("headsign", ""),
                    "company": display_info.get("network", "SNCF"),
                    "transfers": journey["nb_transfers"],
                    "co2_emission": journey.get("co2_emission", {}).get("value", 0),
                    "price": parse_fare_info(journey.get("fare", {})),
                }

                # Log des détails pour debug
                logger.debug(f"Train details: {train}")

                trains.append(train)

        return {
            "status": "success",
            "trains": trains,
            "count": len(trains),
            "search_parameters": {
                "from": params.origin_city,
                "to": params.destination_city,
                "date": params.departure_date,
                "time": params.departure_time or "00:00",
            },
        }

    except Exception as e:
        logger.error(f"❌ Error in train search: {str(e)}")
        return {"status": "error", "message": str(e), "parameters": search_params}
