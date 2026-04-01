import pymysql
import os
from dotenv import load_dotenv

load_dotenv(override=True)

def test_json_set():
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "masterai"),
        cursorclass=pymysql.cursors.DictCursor
    )
    with conn.cursor() as cursor:
        # Get current data
        cursor.execute("SELECT data FROM roadmaps WHERE id = 5")
        row = cursor.fetchone()
        if not row:
            print("Row 5 not found")
            return
            
        print("BEFORE:", row["data"])
        
        # Apply JSON_SET
        # Note: in standard MySQL, JSON_SET(..., true) is allowed for boolean true.
        # But in PyMySQL parameterized queries, we must pass boolean literal in SQL or use json function
        # Or `true` in SQL directly.
        try:
            cursor.execute("""
                UPDATE roadmaps 
                SET data = JSON_SET(
                    IFNULL(data, '{}'), 
                    '$.is_saved', true,
                    '$.source', IFNULL(JSON_UNQUOTE(JSON_EXTRACT(data, '$.source')), 'Explore')
                )
                WHERE id = 5
            """)
            conn.commit()
            print("Update executed.")
        except Exception as e:
            print("UPDATE failed:", e)
            
        # Select after
        cursor.execute("SELECT data FROM roadmaps WHERE id = 5")
        row2 = cursor.fetchone()
        print("AFTER:", row2["data"])

if __name__ == "__main__":
    test_json_set()
