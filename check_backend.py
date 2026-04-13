import requests
try:
    r = requests.get('http://127.0.0.1:8000/api/health')
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"Error: {e}")
