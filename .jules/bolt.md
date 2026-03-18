## 2025-05-15 — Enforced Fail-Fast for Sensitive Credentials

Learning: Hardcoded credential fallbacks in environment variable lookups (e.g., `os.getenv("DATABASE_URL", "...")`) create a security risk where applications might silently use default, insecure credentials if the environment is misconfigured.

Action: Replaced all instances of `os.getenv` for sensitive credentials (DATABASE_URL, SYNC_DATABASE_URL, REDIS_URL, API_KEY) with explicit checks that raise `ValueError` or `HTTPException` if the variable is missing.

## 2026-03-17 — Missing Indexes on High Read Tables

Learning:
The database model for `Message` tracks raw WhatsApp ingestion traffic. However, its primary access patterns (`get_recent_messages` and `get_group_stats`) filter intensely on `group_id` and order by `timestamp`, both of which were unindexed. The `Summary` table similarly lacked an index on `group_id`.

Action:
Added `index=True` to `group_id`, `sender_id`, and `timestamp` on the `Message` table, and `group_id` on the `Summary` table. Future model additions must be analyzed for their high-read patterns to determine optimal indices prior to production data scaling.

## 2024-05-24 — I/O Bound AI Processing

Learning:
During the database seeding process, iterating sequentially to execute AI message analysis was extremely slow and synchronous, bottlenecking the initial data ingestion setup.

Action:
Used `asyncio.gather` in `seed.py` to concurrently trigger the I/O-bound `ai_engine.analyze_message` functions, significantly boosting seeding performance. Future async I/O bounded loops should similarly utilize concurrent task execution where applicable.
