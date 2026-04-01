from flask import Blueprint, request, jsonify
from core.ai import chat_complete, get_ai_client
import json
import logging

logger = logging.getLogger(__name__)
career_bp = Blueprint("career", __name__)


@career_bp.get("/insights")
def get_career_insights():
    role = request.args.get("role", "").strip()
    if not role:
        return jsonify({"error": "role query param is required"}), 400

    # If AI is available, generate live insights; otherwise return static fallback
    if get_ai_client():
        try:
            prompt = (
                f'Provide job market insights for the role of "{role}" in India.\n'
                f"Respond with ONLY a valid JSON object — no markdown, no explanation.\n"
                f'Structure: {{"role":"...","demand_score":0.0-1.0,'
                f'"salary_ranges":{{"junior":"...LPA","mid":"...LPA","senior":"...LPA"}},'
                f'"top_skills":[{{"skill":"...","demand":0.0-1.0}}]}}\n'
                f"Include exactly 5 top_skills."
            )

            raw = chat_complete(
                messages=[
                    {"role": "system", "content": "You provide job market data. Reply with raw JSON only."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=512,
            )

            clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            data["role"] = role  # Ensure role matches request
            return jsonify(data)

        except Exception as e:
            logger.error(f"Career Insights AI Error: {e}")
            # Fall through to static data on error

    # Static fallback (used when AI is unavailable or errors out)
    return jsonify({
        "role": role,
        "demand_score": 0.88,
        "salary_ranges": {"junior": "6-10 LPA", "mid": "12-20 LPA", "senior": "25-45 LPA"},
        "top_skills": [
            {"skill": "System Design",       "demand": 0.90},
            {"skill": "Cloud Architecture",  "demand": 0.85},
            {"skill": "Data Structures",     "demand": 0.82},
            {"skill": "Problem Solving",     "demand": 0.95},
            {"skill": "Communication",       "demand": 0.75},
        ],
    })
