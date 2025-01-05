# config.py
from typing import List
from dataclasses import dataclass
from agents.tools.flights_finder import flights_finder
from agents.tools.hotels_finder import hotels_finder
from agents.tools.trains_finder import trains_finder
from agents.tools.jobs_finder import jobs_finder


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


@dataclass
class AgentJobConfig:
    """Configuration pour l'agent de recherche d'emploi"""

    def __init__(self):
        self.model = "gpt-4"
        self.temperature = 0.7
        self.max_results = 10
        self.required_skills = []
        self.remote_options = ["REMOTE", "HYBRID"]

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = []


TOOLS = [flights_finder, hotels_finder, trains_finder]

TOOLS_JOB = [jobs_finder]

# Search Configuration
SEARCH_CONFIG = {
    "keywords": ["Solution Architect", "Technical Architect", "Cloud Architect"],
    "location": "France",
    "experience_level": ["Mid-Senior level", "Senior"],
    "remote_options": ["REMOTE", "HYBRID"],
    "posted_time": "WEEK",
}

# Job Types mapping
JOB_TYPES = {"REMOTE": "2", "HYBRID": "3", "ON-SITE": "1"}

LOCATION_MAPPING = {
    "Paris": "Île-de-France",
    "Lyon": "Auvergne-Rhône-Alpes",
}


# Skills Configuration
SKILLS = {
    "Cloud": [
        "AWS",
        "Azure",
        "GCP",
        "Kubernetes",
        "Docker",
        "Containerization",
        "Microservices",
    ],
    "Languages": [
        "Python",
        "TypeScript",
        "Go",
    ],
    "DevOps": [
        "CI/CD",
        "GitLab",
        "GitHub Actions",
        "ArgoCD",
        "Terraform",
        "Pulumi",
        "Playwright",
        "GitOps",
        "Kubernetes",
        "Helm",
        "Grafana",
        "SonarQube",
        "Datadog",
    ],
    "Architectures": [
        "Microservices",
        "Event-Driven",
        "Serverless",
        "Domain-Driven Design",
        "SOA",
        "API Design",
        "Distributed Systems",
    ],
    "Databases": [
        "PostgreSQL",
        "MongoDB",
        "Cassandra",
        "Redis",
        "DynamoDB",
    ],
}
