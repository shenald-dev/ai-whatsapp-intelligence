# BOLT Run Report

**What changed**:
Refactored `backend/app/api/endpoints.py` to use explicit attribute access (`row.id`, `row.name`) instead of positional tuple indexing (`row[0]`, `row[1]`) for SQLAlchemy 2.0 `Row` objects. Added an entry to `.jules/bolt.md` documenting this optimization.

**Why it matters**:
Positional tuple indexing is fragile; if the order of columns in the database schema or `select()` query changes, the index numbers would break silently, leading to data mapping errors or runtime crashes. Using explicit NamedTuple field access greatly improves code readability, resilience, and maintainability, preventing future regressions.

**How it was verified**:
Verified by running the full backend test suite (`poetry run pytest`), which passed 23/23 tests successfully without regression. Tested for static analysis errors utilizing `ruff`.

**Remaining risk**:
No remaining risk. The `Row` objects natively support NamedTuple attribute access without runtime overhead or complex deserialization.
