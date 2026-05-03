import httpx
import json

def test_campaigns():
    response = httpx.get("http://localhost:8000/api/admin/campaigns")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_campaigns()
