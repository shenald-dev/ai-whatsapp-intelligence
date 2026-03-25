from fastapi.testclient import TestClient
from app.main import app
import os

def test_cors_restricted():
    client = TestClient(app)
    # Testing with an unauthorized origin
    response = client.options(
        "/",
        headers={
            "Origin": "http://malicious.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # When origin is not allowed, FastAPI/Starlette CORSMiddleware
    # returns a simple response WITHOUT CORS headers or with a fail status.
    # Actually, Starlette returns a 200 but WITHOUT the Access-Control-Allow-Origin header if the origin is not allowed.
    assert "access-control-allow-origin" not in response.headers

def test_cors_allowed():
    client = TestClient(app)
    # Testing with an authorized origin
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"
