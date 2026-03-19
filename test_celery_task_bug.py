import asyncio
from unittest.mock import MagicMock, patch
import os

os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

def run_test():
    import threading
    import app.workers.tasks

    with patch("app.workers.tasks.SessionLocal") as mock_session_local:
        # Mock session
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        # Mock message
        mock_msg = MagicMock()
        mock_msg.content = "Test message"
        mock_msg.is_analyzed = False
        mock_session.query.return_value.filter.return_value.first.return_value = mock_msg

        with patch("app.workers.tasks.ai_engine") as mock_ai:
            async def mock_analyze(*args, **kwargs):
                return {"sentiment": "positive", "classification": "task", "topics": ["test"]}
            mock_ai.analyze_message = mock_analyze

            def worker_thread():
                try:
                    res = app.workers.tasks.process_message("123")
                    print("Worker Result:", res)
                except Exception as e:
                    print("Worker Crashed:", type(e).__name__, "-", e)

            t = threading.Thread(target=worker_thread)
            t.start()
            t.join()

if __name__ == "__main__":
    run_test()
