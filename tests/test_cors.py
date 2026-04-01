import urllib.request
import json

print("Testing Backend Registration (CORS and Logic)")

url = "http://localhost:8001/api/v1/auth/register"
headers = {
    "Origin": "http://localhost:8080",
    "Content-Type": "application/json"
}
data = json.dumps({
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "password": "password123"
}).encode('utf-8')

try:
    print("Sending OPTIONS request...")
    req_opt = urllib.request.Request(url, method="OPTIONS")
    req_opt.add_header("Origin", "http://localhost:8080")
    req_opt.add_header("Access-Control-Request-Method", "POST")
    req_opt.add_header("Access-Control-Request-Headers", "content-type")
    
    with urllib.request.urlopen(req_opt) as res_opt:
        print("OPTIONS Status:", res_opt.status)
        print("OPTIONS Headers:", res_opt.headers)

    print("\nSending POST request...")
    req_post = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req_post) as res_post:
        print("POST Status:", res_post.status)
        print("POST Response:", res_post.read().decode('utf-8'))
        
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print("Response:", e.read().decode('utf-8'))
