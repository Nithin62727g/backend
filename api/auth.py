from flask import Blueprint, request, jsonify, g
from datetime import timedelta, datetime
from core.database import get_db
from core.security import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from core.email import send_otp_email
from models.user import row_to_user_response
from api.deps import require_auth
import logging
import random
import string
import re

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

# ── OTP store ────────────────────────────────────────────────────────────────
# Keyed by (email, purpose): {"email|purpose": {"otp": "123456", "expires": datetime}}
# Purpose is "login", "reset", or "signup".  In production use Redis for persistence + TTL.
_otp_store: dict = {}
OTP_EXPIRY_MINUTES = 10

# ── Allowed email domains ─────────────────────────────────────────────────────
ALLOWED_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "yahoo.in", "yahoo.co.uk",
    "outlook.com", "hotmail.com", "live.com",
    "icloud.com", "me.com",
    "saveetha.com", "saveetha.ac.in",
    "protonmail.com", "proton.me",
    "zoho.com", "rediffmail.com",
}


def _make_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _store_otp(email: str, purpose: str, otp: str):
    key = f"{email}|{purpose}"
    _otp_store[key] = {
        "otp": otp,
        "expires": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    }


def _verify_otp(email: str, purpose: str, otp: str) -> tuple[bool, str]:
    """Returns (ok, error_message)."""
    key = f"{email}|{purpose}"
    entry = _otp_store.get(key)
    if not entry:
        return False, "OTP not found. Please request a new one."
    if datetime.utcnow() > entry["expires"]:
        _otp_store.pop(key, None)
        return False, "OTP has expired. Please request a new one."
    if entry["otp"] != otp.strip():
        return False, "Invalid OTP. Please try again."
    _otp_store.pop(key, None)   # invalidate after use
    return True, ""


def _validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, ""


def _validate_email_domain(email: str) -> tuple[bool, str]:
    """Checks that the email's domain is in the allowed list."""
    parts = email.rsplit('@', 1)
    if len(parts) != 2 or not parts[1]:
        return False, "Invalid email address."
    domain = parts[1].lower()
    if domain not in ALLOWED_EMAIL_DOMAINS:
        return False, (
            f"Email domain '@{domain}' is not allowed. "
            "Please use a Gmail, Yahoo, Outlook, Saveetha, or similar account."
        )
    return True, ""


def _update_streak(user: dict, db) -> dict:
    """Calculates and updates the streak based on IST timezone."""
    ist_offset = timedelta(hours=5, minutes=30)
    today_ist = (datetime.utcnow() + ist_offset).date()
    
    last_login = user.get("last_login_date")
    current_streak = user.get("current_streak", 0)
    longest_streak = user.get("longest_streak", 0)
    
    if last_login == today_ist:
        return user  # Already logged in today
        
    if last_login == today_ist - timedelta(days=1):
        current_streak += 1
    else:
        current_streak = 1
        
    longest_streak = max(longest_streak, current_streak)
    
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET current_streak = %s, longest_streak = %s, last_login_date = %s WHERE id = %s",
            (current_streak, longest_streak, today_ist, user["id"])
        )
        db.commit()
        
    user["current_streak"] = current_streak
    user["longest_streak"] = longest_streak
    user["last_login_date"] = today_ist
    return user


# ── Send Signup OTP ───────────────────────────────────────────────────────────

@auth_bp.post("/send-signup-otp")
def send_signup_otp():
    """
    Step 1 of email-verified signup.
    Validates email domain, checks email not already taken, then mails a 6-digit OTP.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email is required"}), 400

    ok, err = _validate_email_domain(email)
    if not ok:
        return jsonify({"error": err}), 400

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "An account with this email already exists."}), 400

    otp = _make_otp()
    _store_otp(email, "signup", otp)

    ok = send_otp_email(email, otp)
    if not ok:
        return jsonify({"error": "Failed to send OTP email. Please try again later."}), 500

    logger.info(f"Signup OTP sent to {email}")
    return jsonify({"message": "Verification code sent. Check your email."}), 200


# ── Register ─────────────────────────────────────────────────────────────────

@auth_bp.post("/register")
def register_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    otp = data.get("otp", "").strip()

    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required"}), 400

    if len(name) < 3:
        return jsonify({"error": "Full name must be at least 3 characters long"}), 400

    if any(char.isdigit() for char in name):
        return jsonify({"error": "Full name cannot contain numbers"}), 400

    if not otp:
        return jsonify({"error": "OTP verification is required. Please verify your email first."}), 400

    # Validate email domain server-side
    ok, err = _validate_email_domain(email)
    if not ok:
        return jsonify({"error": err}), 400

    # Validate password strength
    ok, err = _validate_password(password)
    if not ok:
        return jsonify({"error": err}), 400

    # Verify the signup OTP
    ok, err = _verify_otp(email, "signup", otp)
    if not ok:
        return jsonify({"error": err}), 400

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "An account with this email already exists."}), 400

        hashed = get_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, hashed_password, name) VALUES (%s, %s, %s)",
            (email, hashed, name),
        )
        new_id = cursor.lastrowid
        db.commit()

    logger.info(f"Registered new user: {email}")
    return jsonify({
        "id": str(new_id),
        "email": email,
        "name": name,
        "learning_style": "Visual Learner",
        "xp": 0,
    }), 201


# ── Login (email + password) ─────────────────────────────────────────────────

@auth_bp.post("/login")
def login_user():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

    if not user:
        return jsonify({"error": "Account not found with this email"}), 404

    if not verify_password(password, user["hashed_password"]):
        return jsonify({"error": "Incorrect password"}), 401

    user = _update_streak(user, db)

    token = create_access_token(
        data={"sub": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"User logged in: {email}")
    user_data = row_to_user_response(user)
    user_data["completed_topics"] = []  # Skip DB query on login for speed
    return jsonify({"access_token": token, "token_type": "bearer", "user": user_data})




# ── Me ────────────────────────────────────────────────────────────────────────

@auth_bp.get("/me")
@require_auth
def get_user_profile():
    user_id = g.current_user["id"]
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT topic_id FROM topic_progress WHERE user_id = %s", (user_id,))
        rows = cursor.fetchall()
        completed_topics = [row["topic_id"] for row in rows]
        
    resp = row_to_user_response(g.current_user)
    resp["completed_topics"] = completed_topics
    return jsonify(resp)


# ── Update learning style ─────────────────────────────────────────────────────

@auth_bp.put("/me/learning-style")
@require_auth
def update_learning_style():
    data = request.get_json(silent=True)
    learning_style = (data or {}).get("learning_style", "").strip()
    if not learning_style:
        return jsonify({"error": "learning_style is required"}), 400

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET learning_style = %s WHERE id = %s",
            (learning_style, g.current_user["id"]),
        )
        db.commit()
        cursor.execute("SELECT * FROM users WHERE id = %s", (g.current_user["id"],))
        updated_user = cursor.fetchone()

    return jsonify(row_to_user_response(updated_user))


# ── Onboarding ────────────────────────────────────────────────────────────────

@auth_bp.put("/me/onboarding")
@require_auth
def update_onboarding():
    """Save the 3-step onboarding data for a newly registered user."""
    data = request.get_json(silent=True) or {}

    goal = data.get("goal", "").strip()
    learning_style = data.get("learning_style", "").strip()
    experience_level = data.get("experience_level", "").strip()
    weekly_hours = data.get("weekly_hours")
    target_completion = data.get("target_completion", "").strip()

    if not goal or not learning_style or not experience_level or not target_completion:
        return jsonify({"error": "goal, learning_style, experience_level, and target_completion are required"}), 400

    try:
        weekly_hours_int = int(weekly_hours) if weekly_hours is not None else None
    except (ValueError, TypeError):
        return jsonify({"error": "weekly_hours must be an integer"}), 400

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(
            """UPDATE users
               SET goal = %s, learning_style = %s, experience_level = %s,
                   weekly_hours = %s, target_completion = %s
               WHERE id = %s""",
            (goal, learning_style, experience_level, weekly_hours_int, target_completion, g.current_user["id"]),
        )
        db.commit()
        cursor.execute("SELECT * FROM users WHERE id = %s", (g.current_user["id"],))
        updated_user = cursor.fetchone()

    logger.info(f"Onboarding saved for user {g.current_user['email']}: goal={goal}")
    return jsonify(row_to_user_response(updated_user))


# ── Update Email ──────────────────────────────────────────────────────────────

@auth_bp.put("/me/email")
@require_auth
def update_email():
    data = request.get_json(silent=True) or {}
    new_email = data.get("new_email", "").strip().lower()
    password = data.get("password", "")

    if not new_email or not password:
        return jsonify({"error": "new_email and password are required"}), 400

    user_id = g.current_user["id"]
    db = get_db()
    
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user or not verify_password(password, user["hashed_password"]):
            return jsonify({"error": "Incorrect password"}), 401

        # Check if new email exists
        cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (new_email, user_id))
        if cursor.fetchone():
            return jsonify({"error": "This email is already in use by another account"}), 400

        cursor.execute(
            "UPDATE users SET email = %s WHERE id = %s",
            (new_email, user_id),
        )
        db.commit()

    # Generate a new token since the sub claim changed
    token = create_access_token(
        data={"sub": new_email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info(f"User {user_id} updated email to {new_email}")
    return jsonify({"access_token": token, "token_type": "bearer"})


# ── Update Password ───────────────────────────────────────────────────────────

@auth_bp.put("/me/password")
@require_auth
def update_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "current_password and new_password are required"}), 400
        
    ok, err = _validate_password(new_password)
    if not ok:
        return jsonify({"error": err}), 400

    user_id = g.current_user["id"]
    db = get_db()

    with db.cursor() as cursor:
        cursor.execute("SELECT hashed_password FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user or not verify_password(current_password, user["hashed_password"]):
            return jsonify({"error": "Incorrect current password"}), 401
            
        if verify_password(new_password, user["hashed_password"]):
            return jsonify({"error": "New password cannot be the same as your current password"}), 400
            
        hashed = get_password_hash(new_password)
        cursor.execute(
            "UPDATE users SET hashed_password = %s WHERE id = %s",
            (hashed, user_id),
        )
        db.commit()

    logger.info(f"User {user_id} updated password via profile settings")
    return jsonify({"message": "Password updated successfully"})


# ── Delete Account ────────────────────────────────────────────────────────────

@auth_bp.delete("/me")
@require_auth
def delete_account():
    user_id = g.current_user["id"]
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM roadmap_topics WHERE roadmap_id IN (SELECT id FROM roadmaps WHERE user_id = %s)", (user_id,))
            cursor.execute("DELETE FROM roadmap_modules WHERE roadmap_id IN (SELECT id FROM roadmaps WHERE user_id = %s)", (user_id,))
            cursor.execute("DELETE FROM roadmaps WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM quiz_results WHERE user_id = %s", (user_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
        logger.info(f"User account {user_id} deleted.")
        return jsonify({"message": "Account successfully deleted"}), 200
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete account {user_id}: {e}")
        return jsonify({"error": "Failed to delete account"}), 500


# ── Forgot Password — Step 1: send OTP ───────────────────────────────────────

@auth_bp.post("/forgot-password")
def forgot_password():
    """Send a password-reset OTP to the user's email."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email is required"}), 400

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

    if not user:
        # Generic response — don't reveal if the email is registered
        return jsonify({"message": "If that email exists, a reset code has been sent."}), 200

    otp = _make_otp()
    _store_otp(email, "reset", otp)

    ok = send_otp_email(email, otp)
    if not ok:
        return jsonify({"error": "Failed to send OTP email. Please try again later."}), 500

    logger.info(f"Password reset OTP sent to {email}")
    return jsonify({"message": "If that email exists, a reset code has been sent."}), 200


# ── Forgot Password — Step 2: reset with OTP ─────────────────────────────────

@auth_bp.post("/reset-password")
def reset_password():
    """Validate reset OTP and update the user's password."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    otp = data.get("otp", "").strip()
    new_password = data.get("new_password", "")

    if not email or not otp or not new_password:
        return jsonify({"error": "email, otp, and new_password are required"}), 400
    
    ok, err = _validate_password(new_password)
    if not ok:
        return jsonify({"error": err}), 400

    ok, err = _verify_otp(email, "reset", otp)
    if not ok:
        return jsonify({"error": err}), 400

    db = get_db()
    with db.cursor() as cursor:
        cursor.execute("SELECT hashed_password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user and verify_password(new_password, user["hashed_password"]):
            return jsonify({"error": "New password cannot be the same as your old password"}), 400

        hashed = get_password_hash(new_password)
        cursor.execute("UPDATE users SET hashed_password = %s WHERE email = %s", (hashed, email))
        db.commit()

    logger.info(f"Password reset successful for {email}")
    return jsonify({"message": "Password reset successful. You can now log in."}), 200
