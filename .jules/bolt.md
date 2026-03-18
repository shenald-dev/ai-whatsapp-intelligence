## 2024-05-24 — Missing Database Indexes on Hot Paths

Learning:
The core tables `messages` and `summaries` lacked indexes on their most frequently queried columns (`group_id` and `timestamp`), which would lead to severe performance degradation via full-table scans as data volume increases.

Action:
Refactored the dashboard API to push all group statistics aggregations (e.g., analyzed counts, sentiment breakdown, classification detection) down to the PostgreSQL database level using optimized `GROUP BY` and `CASE` aggregation queries (`func.sum(case(...))`). Ensure future metrics queries follow this pattern, shifting computational weight off the API nodes and taking advantage of SQL optimizations.

## 2026-03-17 — Missing Indexes on High Read Tables

Learning:
The database model for `Message` tracks raw WhatsApp ingestion traffic. However, its primary access patterns (`get_recent_messages` and `get_group_stats`) filter intensely on `group_id` and order by `timestamp`, both of which were unindexed. The `Summary` table similarly lacked an index on `group_id`.

Action:
Added `index=True` to `group_id`, `sender_id`, and `timestamp` on the `Message` table, and `group_id` on the `Summary` table. Future model additions must be analyzed for their high-read patterns to determine optimal indices prior to production data scaling.
