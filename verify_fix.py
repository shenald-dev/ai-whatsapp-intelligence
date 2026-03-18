import os
import sys

# Mock common modules that might be missing
from unittest.mock import MagicMock

# Create a mock HTTPException class
class MockHTTPException(Exception):
    def __init__(self, status_code, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

# Define sub-mocks for packages
sqlalchemy_mock = MagicMock()
sqlalchemy_ext_asyncio_mock = MagicMock()
sqlalchemy_orm_mock = MagicMock()
sqlalchemy_future_mock = MagicMock()

sys.modules["sqlalchemy"] = sqlalchemy_mock
sys.modules["sqlalchemy.ext.asyncio"] = sqlalchemy_ext_asyncio_mock
sys.modules["sqlalchemy.orm"] = sqlalchemy_orm_mock
sys.modules["sqlalchemy.future"] = sqlalchemy_future_mock

dotenv_mock = MagicMock()
sys.modules["dotenv"] = dotenv_mock

celery_mock = MagicMock()
sys.modules["celery"] = celery_mock

fastapi_mock = MagicMock()
fastapi_mock.HTTPException = MockHTTPException
fastapi_security_api_key_mock = MagicMock()
fastapi_middleware_cors_mock = MagicMock()
sys.modules["fastapi"] = fastapi_mock
sys.modules["fastapi.security.api_key"] = fastapi_security_api_key_mock
sys.modules["fastapi.middleware.cors"] = fastapi_middleware_cors_mock

pydantic_mock = MagicMock()
sys.modules["pydantic"] = pydantic_mock

# Add backend to path and treat app as a package by adding the parent
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Mock sub-modules that might cause issues if they try to import things
sys.modules["app.db.models"] = MagicMock()
sys.modules["app.ai.engine"] = MagicMock()
sys.modules["app.api.schemas"] = MagicMock()
sys.modules["app.api.endpoints"] = MagicMock()

# Set required env vars to avoid failures in other modules when importing main
os.environ["DATABASE_URL"] = "mock_db_url"
os.environ["SYNC_DATABASE_URL"] = "mock_sync_db_url"
os.environ["REDIS_URL"] = "mock_redis_url"

def test_database_url():
    print("Testing DATABASE_URL enforcement...")
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]

    try:
        from app.db import database
        import importlib
        importlib.reload(database)
        print("FAILED: DATABASE_URL not enforced")
        return False
    except ValueError as e:
        if "DATABASE_URL environment variable is not set" in str(e):
            print("PASSED: DATABASE_URL enforcement caught")
            os.environ["DATABASE_URL"] = "mock_db_url"
            return True
        else:
            print(f"FAILED: Unexpected error message: {e}")
            return False
    except Exception as e:
        print(f"FAILED: Unexpected exception: {type(e).__name__}: {e}")
        return False

def test_sync_database_url():
    print("Testing SYNC_DATABASE_URL enforcement...")
    if "SYNC_DATABASE_URL" in os.environ:
        del os.environ["SYNC_DATABASE_URL"]

    try:
        from app.workers import tasks
        import importlib
        importlib.reload(tasks)
        print("FAILED: SYNC_DATABASE_URL not enforced")
        return False
    except ValueError as e:
        if "SYNC_DATABASE_URL environment variable is not set" in str(e):
            print("PASSED: SYNC_DATABASE_URL enforcement caught")
            os.environ["SYNC_DATABASE_URL"] = "mock_sync_db_url"
            return True
        else:
            print(f"FAILED: Unexpected error message: {e}")
            return False
    except Exception as e:
        print(f"FAILED: Unexpected exception: {type(e).__name__}: {e}")
        return False

def test_redis_url():
    print("Testing REDIS_URL enforcement...")
    if "REDIS_URL" in os.environ:
        del os.environ["REDIS_URL"]

    try:
        from app.workers import celery_config
        import importlib
        importlib.reload(celery_config)
        print("FAILED: REDIS_URL not enforced")
        return False
    except ValueError as e:
        if "REDIS_URL environment variable is not set" in str(e):
            print("PASSED: REDIS_URL enforcement caught")
            os.environ["REDIS_URL"] = "mock_redis_url"
            return True
        else:
            print(f"FAILED: Unexpected error message: {e}")
            return False
    except Exception as e:
        print(f"FAILED: Unexpected exception: {type(e).__name__}: {e}")
        return False

async def test_api_key():
    print("Testing API_KEY enforcement...")
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]

    try:
        from app import main
        import importlib
        importlib.reload(main)

        await main.get_api_key("some-key")
        print("FAILED: API_KEY not enforced")
        return False
    except MockHTTPException as e:
        if e.status_code == 500 and "API_KEY" in e.detail:
             print("PASSED: API_KEY enforcement caught")
             return True
        else:
             print(f"FAILED: Unexpected MockHTTPException: {e.status_code} - {e.detail}")
             return False
    except Exception as e:
             print(f"FAILED: Unexpected error: {type(e).__name__}: {e}")
             return False

import asyncio
if __name__ == "__main__":
    results = []
    results.append(test_database_url())
    results.append(test_sync_database_url())
    results.append(test_redis_url())
    results.append(asyncio.run(test_api_key()))

    if all(results):
        print("\nAll security enforcement tests PASSED")
        sys.exit(0)
    else:
        print("\nSome security enforcement tests FAILED")
        sys.exit(1)
