import urllib.request
import urllib.error
import json

url = 'http://localhost:8001/api/v1/auth/register'
data = json.dumps({'email': 'test500@mail.com', 'name': 'Test', 'password': 'password123'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as res:
        print("Success:", res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}:")
    print(e.read().decode('utf-8'))
except Exception as e:
    print("Other error:", str(e))
