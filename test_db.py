import pymysql
import os
from dotenv import load_dotenv

load_dotenv(override=True)

def test_db():
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "masterai"),
        cursorclass=pymysql.cursors.DictCursor
    )
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, data FROM roadmaps ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        for r in rows:
            print(f"ID {r['id']} -> {r['data']}")

if __name__ == "__main__":
    test_db()
