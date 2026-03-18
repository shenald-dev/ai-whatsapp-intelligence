## 2025-05-15 — Enforced Fail-Fast for Sensitive Credentials

Learning: Hardcoded credential fallbacks in environment variable lookups (e.g., `os.getenv("DATABASE_URL", "...")`) create a security risk where applications might silently use default, insecure credentials if the environment is misconfigured.

Action: Replaced all instances of `os.getenv` for sensitive credentials (DATABASE_URL, SYNC_DATABASE_URL, REDIS_URL, API_KEY) with explicit `os.environ.get` checks that raise `ValueError` or `HTTPException` if the variable is missing. Added a `verify_fix.py` script to automate this check across the backend.

## 2026-03-17 — Missing Indexes on High Read Tables

Learning:
The database model for `Message` tracks raw WhatsApp ingestion traffic. However, its primary access patterns (`get_recent_messages` and `get_group_stats`) filter intensely on `group_id` and order by `timestamp`, both of which were unindexed. The `Summary` table similarly lacked an index on `group_id`.

Action:
Added `index=True` to `group_id`, `sender_id`, and `timestamp` on the `Message` table, and `group_id` on the `Summary` table. Future model additions must be analyzed for their high-read patterns to determine optimal indices prior to production data scaling.

## 2024-06-01 — Concurrent AI Analysis in Seed Generation

Learning:
Sequential execution of I/O-bound tasks, such as AI analysis via LLM APIs, significantly bottlenecks bulk data processing. In the `seed.py` script, processing 20 messages sequentially was taking ~2 seconds (simulated), which scales linearly with the number of messages.

Action:
Refactored the message seeding loop to collect AI analysis coroutines and execute them concurrently using `asyncio.gather`. This change reduced the total analysis time for 20 messages from ~2 seconds to ~0.1 seconds, achieving a ~95% performance improvement in I/O-bound throughput during database seeding.
