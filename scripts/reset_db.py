"""
Full Database Reset & Initialization for MasterAI (MariaDB).
Drops the existing database and recreates it with all required tables.
Usage: python scripts/reset_db.py
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
import pymysql

DDL = [
    # Users table
    """CREATE TABLE users (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        email           VARCHAR(255) NOT NULL UNIQUE,
        name            VARCHAR(255) NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        learning_style  VARCHAR(100) NOT NULL DEFAULT 'Visual Learner',
        xp              INT NOT NULL DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

    # Roadmaps table
    """CREATE TABLE roadmaps (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT NULL,
        goal_title  VARCHAR(512) NOT NULL,
        data        JSON NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",

    # Quiz Results table
    """CREATE TABLE quiz_results (
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
    """CREATE TABLE topic_progress (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        user_id     INT NOT NULL,
        topic_id    VARCHAR(512) NOT NULL,
        xp_earned   INT NOT NULL DEFAULT 0,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_topic (user_id, topic_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;""",
]

def reset_db():
    print(f"Connecting to {settings.DB_HOST}:{settings.DB_PORT} ...")
    try:
        conn = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset="utf8mb4",
            autocommit=True
        )
        with conn.cursor() as cursor:
            print(f"Dropping database {settings.DB_NAME} (if exists)...")
            cursor.execute(f"DROP DATABASE IF EXISTS {settings.DB_NAME}")
            
            print(f"Creating database {settings.DB_NAME}...")
            cursor.execute(f"CREATE DATABASE {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            
            cursor.execute(f"USE {settings.DB_NAME}")
            
            for i, ddl in enumerate(DDL):
                print(f"  Creating table {i+1}/{len(DDL)} ...")
                cursor.execute(ddl)
                
        conn.close()
        print("\n✅ Database reset and initialized successfully.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_db()
