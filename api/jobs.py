from flask import Blueprint, request, jsonify
from core.config import settings
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger(__name__)
jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.get("/search")
def search_jobs():
    role = request.args.get("role", "").strip()
    location = request.args.get("location", "us").strip() # default country code 'us'
    
    if not role:
        return jsonify({"error": "role parameter is required"}), 400

    app_id = settings.ADZUNA_APP_ID
    app_key = settings.ADZUNA_APP_KEY
    
    if not app_id or not app_key or app_id == "YOUR_FREE_ADZUNA_APP_ID_HERE":
        # Return mock data if no real API key is provided
        return jsonify({
            "role": role,
            "jobs": [
                {
                    "title": f"Junior {role}",
                    "company": "Tech Innovators Inc.",
                    "location": "Remote",
                    "salary": "$70,000 - $90,000",
                    "url": "https://example.com/job/1"
                },
                {
                    "title": f"Senior {role} Engineer",
                    "company": "Global Solutions Ltd.",
                    "location": "New York, USA",
                    "salary": "$120,000 - $150,000",
                    "url": "https://example.com/job/2"
                },
                {
                    "title": f"{role} Specialist",
                    "company": "Startup Hub",
                    "location": "San Francisco, CA",
                    "salary": "$100,000+",
                    "url": "https://example.com/job/3"
                }
            ],
            "is_mock": True
        })

    try:
        # Adzuna API format: /v1/api/jobs/{country}/search/{page}
        query = urllib.parse.quote(role)
        url = f"https://api.adzuna.com/v1/api/jobs/{location}/search/1?app_id={app_id}&app_key={app_key}&results_per_page=5&what={query}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        jobs = []
        for item in data.get("results", []):
            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")
            
            salary_str = "Competitive"
            if salary_min and salary_max:
                salary_str = f"${int(salary_min):,} - ${int(salary_max):,}"
            elif salary_min:
                salary_str = f"From ${int(salary_min):,}"
                
            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("company", {}).get("display_name", "Unknown Company"),
                "location": item.get("location", {}).get("display_name", "Remote / Various"),
                "salary": salary_str,
                "url": item.get("redirect_url", "")
            })
            
        return jsonify({"role": role, "jobs": jobs})
        
    except Exception as e:
        logger.error(f"Adzuna API Error: {e}")
        return jsonify({"error": "Failed to fetch jobs from Adzuna"}), 500
