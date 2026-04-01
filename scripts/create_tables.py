"""
Run once to create all required MariaDB tables.
Usage: python scripts/create_tables.py
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
import pymysql
import pymysql.cursors

DDL = [
    # Users table
    """CREATE TABLE IF NOT EXISTS users (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        email           VARCHAR(255) NOT NULL UNIQUE,
        name            VARCHAR(255) NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        learning_style  VARCHAR(100) NOT NULL DEFAULT 'Visual Learner',
        xp              INT NOT NULL DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

    # Roadmaps table
    """CREATE TABLE IF NOT EXISTS roadmaps (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT NULL,
        goal_title  VARCHAR(512) NOT NULL,
        data        JSON NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

    # Quiz Results table
    """CREATE TABLE IF NOT EXISTS quiz_results (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT NULL,
        topic       VARCHAR(255) NOT NULL,
        score       INT NOT NULL,
        max_score   INT NOT NULL,
        xp_earned   INT NOT NULL DEFAULT 0,
        passed      TINYINT(1) NOT NULL DEFAULT 0,
        taken_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

    # Topic progress table
    """CREATE TABLE IF NOT EXISTS topic_progress (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT NOT NULL,
        topic_id    VARCHAR(512) NOT NULL,
        xp_earned   INT NOT NULL DEFAULT 0,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_topic (user_id, topic_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",
]

# Safe column additions for existing tables (idempotent – ignore duplicate-column errors)
MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS goal VARCHAR(255) NULL;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS experience_level VARCHAR(50) NULL;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_hours INT NULL;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS target_completion VARCHAR(50) NULL;",
]

def main():
    print(f"Connecting to {settings.DB_HOST}:{settings.DB_PORT} / {settings.DB_NAME} ...")
    try:
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            cursorclass=pymysql.cursors.DictCursor,
            charset="utf8mb4",
        )
        with conn.cursor() as cursor:
            # Create DB if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME}")
            cursor.execute(f"USE {settings.DB_NAME}")
            
            for ddl in DDL:
                # Extract table name from DDL
                words = ddl.split()
                if "TABLE" in words:
                    table_name = words[words.index("TABLE") + 2]
                    print(f"  Ensuring table {table_name} ...", end=" ")
                    cursor.execute(ddl)
                    print("OK")

            # Run migrations (idempotent column additions)
            print("  Running column migrations ...")
            for migration in MIGRATIONS:
                try:
                    cursor.execute(migration)
                    print(f"    OK: {migration[:60]}")
                except Exception as mig_err:
                    print(f"    SKIP (already exists or error): {mig_err}")
        conn.commit()
        conn.close()
        print("All tables initialized successfully.")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
