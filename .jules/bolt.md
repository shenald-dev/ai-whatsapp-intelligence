## 2024-05-24 — Missing Database Indexes on Hot Paths

Learning:
The core tables `messages` and `summaries` lacked indexes on their most frequently queried columns (`group_id` and `timestamp`), which would lead to severe performance degradation via full-table scans as data volume increases.

Action:
When reviewing database models, always verify that columns frequently used in `WHERE` and `ORDER BY` clauses of the API layer have appropriate indexes defined.
