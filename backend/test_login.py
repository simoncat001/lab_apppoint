import requests
import json
import os

# Disable proxy
os.environ["NO_PROXY"] = "127.0.0.1,localhost"

urls = [
    "http://127.0.0.1:8000/api/auth/login/json",
    "http://localhost:8000/api/auth/login/json"
]
payload = {"username": "admin", "password": "admin"}
headers = {"Content-Type": "application/json"}

for url in urls:
    print(f"Testing {url}...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
