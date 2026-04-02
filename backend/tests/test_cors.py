from fastapi.testclient import TestClient
from app.main import app

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

def test_cors_restricted_methods():
    client = TestClient(app)
    # DELETE is not in the allowed methods
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "DELETE",
        },
    )
    # If the requested method is not allowed, the response should not include the CORS headers for that method
    allowed_methods = response.headers.get("access-control-allow-methods", "")
    assert "DELETE" not in allowed_methods

def test_cors_restricted_headers():
    client = TestClient(app)
    # X-Custom-Header is not in the allowed headers
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Custom-Header",
        },
    )
    allowed_headers = response.headers.get("access-control-allow-headers", "")
    assert "X-Custom-Header" not in allowed_headers
