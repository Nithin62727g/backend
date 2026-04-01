import urllib.request
import json

url = "http://127.0.0.1:5000/v1/mentor/chat"
data = json.dumps({"message": "hello"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req) as res:
        print("Status:", res.status)
        print("Response:", res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print("Response:", e.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
