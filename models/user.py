from datetime import datetime
from typing import Optional


def row_to_user_response(row: dict) -> dict:
    """Convert a MariaDB users row to a JSON-serializable dict for API responses."""
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "learning_style": row.get("learning_style") or "Visual Learner",
        "xp": row.get("xp", 0),
        "goal": row.get("goal"),
        "experience_level": row.get("experience_level"),
        "weekly_hours": row.get("weekly_hours"),
        "target_completion": row.get("target_completion"),
        "current_streak": row.get("current_streak", 0),
        "longest_streak": row.get("longest_streak", 0),
        "last_login_date": row["last_login_date"].isoformat() if row.get("last_login_date") else None,
    }
