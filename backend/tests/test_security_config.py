import os
import pytest
from unittest.mock import patch

def test_database_url_enforced():
    with patch.dict(os.environ, {}, clear=True):
        # We need to reload the module to trigger the check if it was already imported
        # But in a fresh test environment, it should be fine.
        # However, to be safe and actually test the logic:
        import importlib
        import app.db.database
        with pytest.raises(ValueError) as excinfo:
            importlib.reload(app.db.database)
        assert "DATABASE_URL environment variable is not set" in str(excinfo.value)

def test_sync_database_url_enforced():
    with patch.dict(os.environ, {}, clear=True):
        import importlib
        import app.workers.tasks
        with pytest.raises(ValueError) as excinfo:
            importlib.reload(app.workers.tasks)
        assert "SYNC_DATABASE_URL environment variable is not set" in str(excinfo.value)

def test_redis_url_enforced():
    with patch.dict(os.environ, {}, clear=True):
        import importlib
        import app.workers.celery_config
        with pytest.raises(ValueError) as excinfo:
            importlib.reload(app.workers.celery_config)
        assert "REDIS_URL environment variable is not set" in str(excinfo.value)

@pytest.mark.asyncio
async def test_api_key_enforced():
    from app.main import get_api_key
    with patch.dict(os.environ, {}, clear=True):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await get_api_key("some-key")
        assert excinfo.value.status_code == 500
        assert "API_KEY environment variable is not set" in excinfo.value.detail
