## APEX FORGE Run Report

**What changed:**
1. Replaced positional indexing (`row[0]`, `row[1]`) with explicit NamedTuple attribute access (`row.id`, `row.name`, `row.content`, etc.) when mapping trusted SQLAlchemy `Row` tuples into Pydantic models in dashboard API endpoints (`get_groups` and `get_recent_messages`).
2. Updated Pytest mocks in `backend/tests/test_dashboard.py` to match the SQLAlchemy `Row` attribute behavior.
3. Synchronized dependency lockfiles across both Python and Node.js components.
4. Cut a new release and updated versions to `1.0.29` consistently across `collector/package.json`, `backend/pyproject.toml`, `backend/app/main.py`, and `CHANGELOG.md`.

**Why it matters:**
Using explicit attribute access for SQLAlchemy `Row` mapping enforces better code maintainability, clarity, and prevents downstream regression vulnerabilities (silent mapping bugs) that could occur if database columns are reordered or added within the `select()` statements.

**How it was verified:**
The modification was completely verified by applying tests over the refactored endpoints. `test_dashboard.py` was updated, and the full backend suite (`poetry run pytest`) as well as the Node.js suite (`npm run test`) were run, both passing 100%. Lockfile sync was verified via `git status` and a code review tool confirmed changes as commit-ready.

**Is the repository ready?**
Yes, all tests pass successfully, lockfiles are synchronized, the versions align, the repository is verified clean via linter (`ruff`/`vulture`), and the commit is correctly tagged.

**Remaining limitation or risk:**
There are no major remaining technical limitations or newly introduced risks. The changes are strictly behavioral-preserving implementations explicitly allowed by the ORM architecture.
