## APEX FORGE Run Report

**What changed:**
Modified the `process_message` Celery task in `backend/app/workers/tasks.py` to use `load_only` when fetching the `Message` model via `session.get()`. This specifically queries only the required columns (`is_analyzed`, `content`, `group_id`, `sender_id`). Added an inline comment to warn against adding future unused fields without adding them to `load_only`. Added a learning to `.jules/bolt.md`.

**Why it matters:**
Previously, the worker was eager-loading all mapped columns from the database, including the potentially large `Text` payload (`content` column is up to 64KB) and other metadata that was not needed for the task logic. By using `load_only`, we defer the loading of unused columns, saving database bandwidth and reducing memory allocation overhead within the Celery worker background processes.

**How it was verified:**
Ran the full test suite for the backend (`pytest`) and the collector (`npm test`). All tests passed successfully, confirming the changes did not introduce regressions or violate ORM contracts.

**Remaining Risk:**
If new fields are accessed in the task logic in the future without adding them to the `load_only` options, SQLAlchemy will transparently trigger lazy loading, resulting in an N+1 query pattern. The inline comment mitigates this risk by documenting the constraint.
