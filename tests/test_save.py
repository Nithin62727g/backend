import sys
import os
import json
from dotenv import load_dotenv
import pymysql

load_dotenv(override=True)

def test_json():
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", "root"),
        database=os.environ.get("DB_NAME", "masterai"),
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cursor:
            # Get a roadmap ID
            cursor.execute("SELECT id, data FROM roadmaps LIMIT 1")
            row = cursor.fetchone()
            if not row:
                print("No roadmaps to test.")
                return
            
            roadmap_id = row['id']
            print(f"Testing with Roadmap ID: {roadmap_id}")
            
            # Print initial
            print("Initial Data:")
            print(str(row['data'])[:100])
            
            # Update
            cursor.execute(
                "UPDATE roadmaps SET data = JSON_SET(data, '$.is_saved', true) WHERE id = %s",
                (roadmap_id,)
            )
            conn.commit()
            
            # Fetch again
            cursor.execute("SELECT data FROM roadmaps WHERE id = %s", (roadmap_id,))
            updated_row = cursor.fetchone()
            print("\nUpdated Data:")
            print(str(updated_row['data'])[:100])
            
            if 'is_saved' in updated_row['data']:
                print("\nSUCCESS: is_saved string is in data")
            
            # check json loads
            j = json.loads(updated_row['data'])
            print(f"json parsed is_saved: {j.get('is_saved')}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    test_json()
