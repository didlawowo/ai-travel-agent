# config.py
from typing import List
from dataclasses import dataclass
from agents.tools.flights_finder import flights_finder
from agents.tools.hotels_finder import hotels_finder
from agents.tools.trains_finder import trains_finder


@dataclass
class AgentConfig:
    """Configuration pour l'agent de voyage"""

    def __init__(self):
        self.model = "gpt-4o"
        self.temperature = 0.1
        self.max_results = 5
        self.preferences = []

    model: str = "gpt-4o"
    temperature: float = 0.1
    max_hotels: int = 5
    max_flights: int = 5
    preferences: List[str] = None
    currency: str = "EUR"

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = []


TOOLS = [flights_finder, hotels_finder, trains_finder]
