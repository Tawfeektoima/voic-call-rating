import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.limiter import login_ip_limiter, login_email_limiter

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_limiters():
    login_ip_limiter.reset()
    login_email_limiter.reset()
    yield
    login_ip_limiter.reset()
    login_email_limiter.reset()

def test_login_under_limit_succeeds():
    """Verify that a normal number of login requests does not trigger rate limiting."""
    # Send 4 requests (limit is 5)
    for _ in range(4):
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

def test_login_ip_rate_limiting():
    """Verify that login is rate-limited per IP after exceeding the limit."""
    # Send 5 requests (this consumes all 5 available slots)
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    # The 6th request from the same IP should get 429
    response = client.post(
        "/api/auth/login",
        json={"email": "another_nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 429

def test_login_email_rate_limiting():
    """Verify that login is rate-limited per email."""
    # Send 5 requests for same email
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={"email": "target@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    # The 6th request for same email should get 429
    response = client.post(
        "/api/auth/login",
        json={"email": "target@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 429

def test_rate_limiting_does_not_block_unrelated_endpoints():
    """Verify that rate limit on login does not affect other public endpoints."""
    # Exceed limit on login to trigger 429
    for _ in range(6):
        client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
    
    # Verify that a request to an unrelated public endpoint still works fine
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
