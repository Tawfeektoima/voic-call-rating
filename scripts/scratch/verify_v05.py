import sys
import os

import sys
from unittest.mock import MagicMock
sys.modules['redis'] = MagicMock()
sys.modules['redis.asyncio'] = MagicMock()
sys.modules['groq'] = MagicMock()

# Ensure the root directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_endpoints_registered():
    # Since we don't have a token, we just want to ensure the routes exist.
    # We should get a 401 Unauthorized, not a 404 Not Found.
    
    endpoints = [
        "/api/hr/violations/summary",
        "/api/hr/violations/pending",
        "/api/hr/violations/stats",
        "/api/hr/violations/1"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in [401, 403, 500], f"Endpoint {endpoint} failed to load, got {response.status_code}"
        print(f"{endpoint} is registered (Status: {response.status_code}).")

if __name__ == "__main__":
    test_endpoints_registered()
