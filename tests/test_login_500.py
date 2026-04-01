import urllib.request
import json

data = json.dumps({"email": "test@example.com", "password": "password"}).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8001/api/v1/auth/login", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as f:
        print("Success:", f.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code)
    print(e.read().decode("utf-8", errors="ignore"))
except Exception as e:
    print("Exception:", e)
