import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, date
from api.auth import _update_streak
import pymysql
import pymysql.cursors
from core.config import settings

def test():
    db = pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

    ist_offset = timedelta(hours=5, minutes=30)
    today_ist = (datetime.utcnow() + ist_offset).date()

    # Create dummy user dict
    user = {
        "id": 1, 
        "current_streak": 0, 
        "longest_streak": 0, 
        "last_login_date": None
    }
    
    # Ensure user ID 1 exists
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("INSERT IGNORE INTO users (id, email, hashed_password, name) VALUES (1, 'test@test.com', 'pwd', 'test')")

    # Day 1: First login
    print("Testing First Login")
    user = _update_streak(user, db)
    assert user['current_streak'] == 1
    assert user['last_login_date'] == today_ist
    print("First login OK: Streak is 1")

    # Fast forward: simulate yesterday's login
    print("Testing Consecutive Login")
    yesterday = today_ist - timedelta(days=1)
    with db.cursor() as cursor:
        cursor.execute("UPDATE users SET last_login_date = %s WHERE id = 1", (yesterday,))
    user['last_login_date'] = yesterday
    
    user = _update_streak(user, db)
    assert user['current_streak'] == 2
    print("Consecutive login OK: Streak is 2")

    # Breaking streak
    print("Testing Broken Streak")
    two_days_ago = today_ist - timedelta(days=2)
    with db.cursor() as cursor:
        cursor.execute("UPDATE users SET last_login_date = %s WHERE id = 1", (two_days_ago,))
    user['last_login_date'] = two_days_ago
    
    user = _update_streak(user, db)
    assert user['current_streak'] == 1
    assert user['longest_streak'] == 2
    print("Broken streak OK: Reset back to 1. Longest streak preserved at 2.")

    print("All tests passed!")
    db.close()

if __name__ == "__main__":
    test()
