import urllib.request
import json

url = "http://127.0.0.1:8000/api/chat"
data = json.dumps({"question": "What is the cheapest product?", "session_id": "test1"}).encode("utf-8")
headers = {"Content-Type": "application/json"}

req = urllib.request.Request(url, data=data, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        result = response.read().decode()
        print("SUCCESS:", result)
except Exception as e:
    print("ERROR:", str(e))
