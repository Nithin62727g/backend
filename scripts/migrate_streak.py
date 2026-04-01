import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import pymysql.cursors
from core.config import settings

def migrate_streak():
    connection = None
    try:
        # Establish a single connection directly or via config
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        
        print("Successfully connected to the database")
        with connection.cursor() as cursor:
            # Check if current_streak exists
            cursor.execute("""
                SELECT COUNT(*) as count FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'current_streak'
            """, (settings.DB_NAME,))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("Adding streak columns...")
                cursor.execute("ALTER TABLE users ADD COLUMN current_streak INT NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE users ADD COLUMN longest_streak INT NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE users ADD COLUMN last_login_date DATE NULL")
                print("Successfully added streak columns to users table.")
            else:
                print("Streak columns already exist.")
            
    except pymysql.MySQLError as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if connection is not None and connection.open:
            connection.close()

if __name__ == "__main__":
    migrate_streak()
