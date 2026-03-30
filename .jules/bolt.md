## 2024-03-17 — Refactored group dashboard API to prevent OOM errors and reduce latency

Learning:
The API endpoint that computes group message statistics (`/groups/{group_id}/stats`) previously pulled all message records for a given group into memory to calculate counts in python. In a WhatsApp intelligence monitor handling large volumes of chat data, this would quickly lead to high memory consumption, garbage collection pauses, and eventually out-of-memory errors for groups with thousands of messages.

Action:
Refactored the dashboard API to push all group statistics aggregations (e.g., analyzed counts, sentiment breakdown, classification detection) down to the PostgreSQL database level using optimized `GROUP BY` and `CASE` aggregation queries (`func.sum(case(...))`). Ensure future metrics queries follow this pattern, shifting computational weight off the API nodes and taking advantage of SQL optimizations.

## 2026-03-17 — Missing Indexes on High Read Tables

Learning:
The database model for `Message` tracks raw WhatsApp ingestion traffic. However, its primary access patterns (`get_recent_messages` and `get_group_stats`) filter intensely on `group_id` and order by `timestamp`, both of which were unindexed. The `Summary` table similarly lacked an index on `group_id`.

Action:
Added `index=True` to `group_id`, `sender_id`, and `timestamp` on the `Message` table, and `group_id` on the `Summary` table. Future model additions must be analyzed for their high-read patterns to determine optimal indices prior to production data scaling.

## 2024-05-18 — Refactored data seeding script to use asyncio.gather

Learning:
The database seeding script (`backend/seed.py`) was running AI analysis tasks sequentially in a loop, creating an I/O-bound bottleneck due to the nature of `ai_engine.analyze_message` and causing significant delays.

Action:
Refactored the data seeding process to execute AI analysis concurrently using `asyncio.gather`. Future bulk processing operations that depend on I/O-bound tasks should follow this concurrent execution pattern.

## 2024-05-18 — Enforce environment variables for sensitive credentials

Learning:
Multiple modules in the project relied on hardcoded default values for critical secrets and infrastructure URLs (e.g. `DATABASE_URL`, `API_KEY`, `REDIS_URL`). This exposes secure defaults when environments are misconfigured and allows applications to startup pointing to incorrect, insecure development databases when running in a production or staging cluster.

Action:
Refactored the core configuration blocks to explicitly fail fast by raising a `ValueError` (or throwing an `Error` in Node.js) when required environment variables are absent. Always enforce explicit environment variables for sensitive credentials and connections, rejecting hardcoded fallbacks to guarantee predictable, secure deployments.

## 2024-03-24 — Fixed asyncio event loop deprecation in Celery worker

Learning:
The Celery worker `process_message` task was manually managing the asyncio event loop using `asyncio.get_event_loop()`, which throws deprecation warnings and can cause `RuntimeError` in newer Python versions (3.10+) when called outside the main thread without an existing loop.

Action:
Refactored the synchronous to asynchronous execution bridge in the Celery worker to use `asyncio.run()`. This cleanly handles event loop creation and teardown. Future asynchronous calls within synchronous contexts should prefer `asyncio.run()` to prevent event loop lifecycle issues.

## 2024-05-18 — Use SimpleLRUCache to reduce database I/O for entity existence checks

Learning:
The webhook `ingest_message` endpoint made redundant DB calls to check if a group or user existed for every message, unnecessarily hitting the database during high-traffic message ingestion events and causing a database bottleneck.

Action:
Implemented an in-memory `SimpleLRUCache` (via `collections.OrderedDict`) to keep track of known `group_id` and `user_id`s, reducing DB `get` and `add` operations for frequently seen entities. Crucially, cache entries are only populated after a successful database commit to prevent cache poisoning on rollback. We should continue caching frequently checked, immutable (or rarely mutating) identities across APIs.

## 2024-05-18 — Activated Celery Background Task for AI Enrichment

Learning:
The webhook `ingest_message` endpoint successfully saved messages to the database but merely had a placeholder comment `# NOTE: Here we would trigger a Celery task...` instead of actually executing the background processing step. This caused the core AI enrichment functionality to be skipped during message ingestion.

Action:
Imported `celery_app` from `.workers.celery_config` and called `celery_app.send_task("enrich_message", args=[msg.id])` to properly trigger the AI background task after committing a new message to the database. Additionally, added a `unittest.mock.patch` for `app.main.celery_app.send_task` in the `test_ingest_message_caching` test to avoid requiring a real Redis backend during automated test runs. Always ensure that the functional loop of features is completed, and asynchronous hooks are actually invoked.

## 2026-03-27 — Integrated ChromaDB & Fixed Early Connection Crashes

Learning:
The project's README specifies a vector database (ChromaDB) for semantic search, and `backend/app/db/chroma.py` was created. However, it was not being utilized by any pipelines. Furthermore, importing `chromadb` instantiated a connection at the module level. If the ChromaDB server was down (or in a test environment where it isn't required), simply running tests or importing modules would trigger a `ValueError: Could not connect to a Chroma server` and crash the application entirely.

Action:
Refactored `backend/app/db/chroma.py` to use lazy initialization, instantiating the connection and collection only when a query or insertion is made. Integrated ChromaDB into the Celery task (`backend/app/workers/tasks.py`) and seeding script (`backend/seed.py`) to actively index message content and extracted metadata (`group_id`, `sender_id`, `sentiment`, `classification`). Always decouple external connection logic from module imports to prevent catastrophic application startup failures.

## 2025-03-28 — DB Connection Exhaustion in Celery Tasks

Learning:
Celery workers holding synchronous database transactions open while waiting for external LLM API calls causes database connection pool exhaustion under load, significantly degrading performance and reliability.

Action:
Always release or commit database transactions (e.g. `session.commit()`) before blocking on slow external network I/O in worker tasks, then re-acquire the required objects if necessary afterwards.

## 2025-05-18 — Added webhook idempotency to prevent redundant processing

Learning:
The webhook ingestion endpoint `ingest_message` lacked an idempotency check for incoming messages. If a message payload was delivered multiple times (which is common in webhook architectures, e.g. due to retries or network blips), the endpoint would attempt to process and save the duplicate message, leading to a `500 IntegrityError` or wasted database cycles and background task triggers.

Action:
Added a preemptive idempotency check at the beginning of the `ingest_message` handler in `backend/app/main.py`. The endpoint now verifies if `payload.message_id` already exists in the database. If it does, it immediately returns a `200 OK` with a detail message ("Already ingested"), bypassing further database operations and background tasks. This prevents duplicate errors, reduces unnecessary I/O, and improves system resilience. Future webhook handlers should always include idempotency checks.

## 2026-03-29 — Fixed Timing Attack Vulnerability in API Key Comparison

Learning:
The `get_api_key` dependency function in `backend/app/main.py` was previously using a standard equality operator (`==`) to verify the API key. This exposed the endpoint to timing attacks, where an attacker could theoretically measure the time taken to reject an invalid key and use that information to guess the correct key character by character. Additionally, `datetime.fromtimestamp()` was creating naive datetime objects, which can lead to timezone drift issues when saved to PostgreSQL.

Action:
Refactored `get_api_key` to use `secrets.compare_digest()` for constant-time comparison, mitigating timing attacks. Also updated the timestamp conversion to use `tz=timezone.utc` to ensure timezone-aware datetime objects are stored in the database correctly.
