import os
from typing import Optional, List
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
import serpapi
from loguru import logger

JOB_TYPES = {"REMOTE": "remote", "HYBRID": "hybrid", "ON-SITE": "on-site"}
# Posted time mapping
TIME_FILTERS = {"DAY": "r86400", "WEEK": "r604800", "MONTH": "r2592000"}


class JobSearchInput(BaseModel):
    keywords: List[str] = Field(description="List of job titles to search for")
    location: str = Field(default="France", description="Location for the job search")
    contract_type: Optional[str] = Field(
        default="Prestataire",
        description="Type de contrat (Prestataire, Temps plein, Temps partiel, Stage)",
    )
    experience_level: Optional[List[str]] = Field(
        None, description="Required experience levels"
    )
    remote_options: Optional[List[str]] = Field(
        None, description="Remote work options (REMOTE, HYBRID, ON-SITE)"
    )
    posted_time: Optional[str] = Field(
        None, description="Job posting timeframe (DAY, WEEK, MONTH)"
    )
    required_skills: Optional[List[str]] = Field(
        None, description="Required skills for the position"
    )


class JobSearchInputSchema(BaseModel):
    params: JobSearchInput


@tool(args_schema=JobSearchInputSchema)
def jobs_finder(params: JobSearchInput):
    """
    💼 Find jobs using Google Jobs engine with advanced filtering
    """
    logger.info(f"🔍 Starting job search for keywords: {params.keywords}")
    logger.info(f"📍 Location: {params.location}")

    search_params = {
        "api_key": os.environ.get("SERPAPI_API_KEY"),
        "engine": "google_jobs",
        "hl": "fr",
        "gl": "fr",
        "google_domain": "google.fr",
        "q": " OR ".join(params.keywords),
        "location": params.location,
    }

    # Ajouter les paramètres pour prestataire
    if params.contract_type == "Prestataire":
        search_params.update(
            {
                "udm": "8",
                "uds": "ADvngMjcH0KdF7qGWtwTBrP0nt7dXBqPOYYUZ8YeJINQPXjcMy6xa1ZIqgI9SVl-NE7Ng9_0jfFVIMyUsQkA0AGl41EUOE4W48Sq8Hj5YJvIJ9zsAk7low07U5Sc5uK6yejyA6L1CUiL2PwbvWfn9xGf6Yvirq1cGjaD5Qlq0BAvOLxTxhLpn2coGSdkrDdRlYcB9dZc_NIFqsQJqClfje7mJafsn4xZdv9adkEH6ZkvJC0emdYb_Hc9bIOl5M2IfaShzrFtURI-ZzMnmyHVEsn6TWo2x3JUwqB7PyL5UxhYiHKGmPeiaDLtFZSH6sze0hwOpVe1IMvTfqKBnKhke1kBSeqY18eJyA",
            }
        )

    # Add time filter
    if params.posted_time:
        search_params["chips"] = TIME_FILTERS.get(params.posted_time.upper())

    # Add remote options if specified
    if params.remote_options:
        remote_types = [
            JOB_TYPES[opt] for opt in params.remote_options if opt in JOB_TYPES
        ]
        if remote_types:
            search_params["work_from_home"] = ",".join(remote_types)

    logger.info(f"🌐 Prepared search parameters: {search_params}")

    try:
        logger.info("🚀 Making API call to SerpAPI")
        search = serpapi.search(params=search_params)
        logger.info("✅ API call successful")

        if not search.data or "jobs_results" not in search.data:
            logger.warning("⚠️ No jobs found")
            return {
                "status": "no_results",
                "message": "Aucun poste trouvé pour ces critères",
                "search_params": search_params,
            }

        # Process results
        jobs = search.data["jobs_results"]
        logger.info(f"✨ Found {len(jobs)} jobs")

        # Filter by required skills if specified
        if params.required_skills:
            jobs = filter_jobs_by_skills(jobs, params.required_skills)

        # Prepare response
        response = {
            "status": "success",
            "jobs": jobs[:10],
            "total_found": len(jobs),
            "search_parameters": {
                "keywords": params.keywords,
                "location": params.location,
                "contract_type": params.contract_type,
                "experience_level": params.experience_level,
                "remote_options": params.remote_options,
                "posted_time": params.posted_time,
                "required_skills": params.required_skills,
            },
        }

        return response

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error in job search: {error_msg}")
        logger.error(f"Parameters used: {search_params}")
        return {"status": "error", "message": error_msg, "parameters": search_params}


def filter_jobs_by_skills(jobs: list, required_skills: List[str]) -> list:
    """
    🎯 Filter jobs based on required skills in description
    """
    filtered = []
    for job in jobs:
        description = job.get("description", "").lower()
        if all(skill.lower() in description for skill in required_skills):
            filtered.append(job)
    return filtered
