import urllib.request
import urllib.parse
import urllib.error
import json
import os
from dotenv import load_dotenv

load_dotenv(override=True)

def request_json(url, data=None, headers={}):
    h = {'Content-Type': 'application/json'}
    h.update(headers)
    
    if data:
        encoded_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=encoded_data, headers=h, method='POST')
    else:
        req = urllib.request.Request(url, headers=h, method='GET')
        
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() if e.fp else '{}')

def test_save_offline():
    email = "test@example.com"
    password = "password123"
    
    print("Testing offline save...")
    login_status, login_resp = request_json("http://localhost:8001/api/v1/auth/login", {
        "email": "test888@example.com",
        "password": "password123"
    })
    
    if login_status != 200:
        print(f"Login failed, trying register")
        reg_status, reg_resp = request_json("http://localhost:8001/api/v1/auth/register", {
            "email": "test888@example.com",
            "password": "password123",
            "name": "Test User 888"
        })
        if reg_status != 201:
            print(f"Register also failed: {reg_resp}")
            return
        token = reg_resp.get("access_token")
        if not token: # register doesnt return token, need to login
            _, login_resp2 = request_json("http://localhost:8001/api/v1/auth/login", {
                "email": "test888@example.com",
                "password": "password123"
            })
            token = login_resp2.get("access_token")
    else:
        token = login_resp.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    req_data = {
        "goalTitle": "Test Offline Roadmap",
        "description": "Just a test",
        "modules": []
    }
    
    status2, res2 = request_json("http://localhost:8001/api/v1/roadmaps/save-offline", req_data, headers)
    print(f"/save-offline Status code: {status2}")
    print(res2)
    
    if status2 == 200:
        print("SUCCESS! Endpoint works.")
        
    status3, res3 = request_json("http://localhost:8001/api/v1/roadmaps/", None, headers)
    print("Roadmaps count: ", len(res3.get("roadmaps", [])))
    for r in res3.get("roadmaps", []):
        print(f"ID: {r['id']}, Goal: {r['goal_title']}, Saved: {r['data'].get('is_saved')}")

if __name__ == "__main__":
    test_save_offline()
