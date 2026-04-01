import pymysql
import pymysql.cursors
from core.config import settings

def migrate():
    try:
        db = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            charset="utf8mb4",
        )
        print("Connected to DB")
        with db.cursor() as cursor:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN goal VARCHAR(255) NULL AFTER name;")
                print("Added 'goal' column")
            except Exception as e:
                print(f"'goal' column might already exist: {e}")
                
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN experience_level VARCHAR(100) NULL AFTER learning_style;")
                print("Added 'experience_level' column")
            except Exception as e:
                print(f"'experience_level' column might already exist: {e}")

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN weekly_hours INT NULL AFTER experience_level;")
                print("Added 'weekly_hours' column")
            except Exception as e:
                print(f"'weekly_hours' column might already exist: {e}")

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN target_completion VARCHAR(100) NULL AFTER weekly_hours;")
                print("Added 'target_completion' column")
            except Exception as e:
                print(f"'target_completion' column might already exist: {e}")

        db.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Error connecting to the database: {e}")

if __name__ == "__main__":
    migrate()
