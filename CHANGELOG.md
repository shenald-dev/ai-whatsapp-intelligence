# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-11-01

### Major Evolution (v2.0) - Autonomous Group Operations & Real-Time Intelligence Center
* **Autonomous Action Items & Kanban Tracker:** Implemented ActionItem database model, automated extraction of actionable tasks during enrichment, REST endpoints (/api/v1/dashboard/groups/{id}/tasks, /tasks/{id}), and real-time SSE task synchronization with an interactive Kanban board.
* **Instant Incident & Anomaly Alerting:** Added Alert database model, instant pre-enrichment anomaly detector on /ingest and deep classification in workers for outages, security credential exposures, and critical escalations, broadcasting alert.triggered over SSE to a persistent dashboard incident banner.
* **Multi-Model LLM Engine:** Added native configuration for local Ollama (OLLAMA_BASE_URL), OpenRouter, and OpenAI with deterministic heuristic fallback when external AI providers are unavailable.
* **Command Center Dashboard UI:** Upgraded /dashboard to a full-featured 5-tab glassmorphic Command Center (Live Feed, Kanban Board, Incidents, Briefings, Vector RAG) with modal task creation, status filtering, and live SSE event badges.
* **Developer CLI Upgrades:** Expanded python -m app.cli with tasks (terminal Kanban viewer/updater), alerts (incident resolver), and scenario-based simulation (python -m app.cli simulate --scenario [incident|tasks|normal]).

## [Unreleased]
**[Pruned]:** Added multiple endpoint functions to .vulture_whitelist.py to silence static analysis false positives.
**[Optimized]:** Applied explicit HTTP timeouts and retry configurations for ChromaDB client to prevent background worker starvation during network hangs.

### Major Evolution & Next-Gen Capabilities
* **Conversational Vector RAG:** Implemented `/api/v1/dashboard/ask` with LangChain synthesis and citation tracking, allowing natural language question-answering grounded in WhatsApp conversation history.
* **Hybrid Semantic Vector Search:** Implemented `/api/v1/dashboard/search` combining ChromaDB cosine vector search with fallback keyword retrieval and metadata filtering.
* **Autonomous Executive Briefings & Exporters:** Introduced `/api/v1/dashboard/groups/{id}/briefing` and `/export` supporting Markdown, CSV, and JSON formats for executive digests, action items, and decision logs.
* **Real-Time SSE Stream:** Built an in-memory asynchronous broadcast bus and `/api/v1/dashboard/stream` endpoint for instant event streaming to dashboards and listeners.
* **Developer CLI & High-Fidelity Simulator:** Introduced `python -m app.cli` with `health`, `search`, `ask`, `briefing`, and `simulate` commands for seamless testing and demonstration without physical devices.
* **Built-in Glassmorphic Dashboard:** Implemented a modern, zero-dependency interactive dashboard served directly at `/dashboard` with live SSE feed, RAG Q&A, and briefing downloads.
* **Infrastructure Resilience:** Upgraded `ChromaDB` client initialization with automatic fallback from remote HTTP containers to local persistent storage (`.chroma_data`) and in-memory execution.
* **Hygiene & Cleanup:** Removed broken submodule gitlink for `frontend/` and replaced it with clean web client files; pruned orphaned root `package-lock.json`.

* **Reliability:** Hardened message collection pipeline in collector with strict entity ID validation, lifted string truncation helper out of the per-message callback hot path, and sanitized timestamps and media flags to eliminate 422 ingestion validation errors.
* **Security:** Centralized database connection URI sanitization in `app.db.database` and protected dashboard endpoints (`/groups`, `/groups/{id}/stats`, `/groups/{id}/messages`) against credential leakage in server logs on database connection errors.
* **Hygiene:** Pruned orphaned merge conflict artifacts (`CHANGELOG.md.master` and `.jules/warden.md.master`).
**[Assurance]:** Updated psycopg2-binary to 2.9.13 and completed Warden lifecycle audit without identifying regressions.

**[Fixed]:** Fixed unused import warnings for `pytest` and `unittest.mock.MagicMock` in `backend/tests/test_orm_bypass.py` and `backend/tests/test_tasks.py` and ignored module-level import errors (E402) in `backend/tests/test_tasks.py` to achieve zero warnings from static code analysis (ruff).

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Fixed duplicate assignment logic in `process_message` Celery task. Fixed missing `await` regression in `forwardToBackend` call inside `collector/src/index.js` message handler.
* **Upgrades:** Addressed NPM high severity vulnerabilities in the Node.js collector dependencies.
* **Pruning:** Pruned dead duplicate assignments in `tasks.py`. Pruned `__pycache__` artifacts to maintain codebase entropy.

## [1.0.28] - 2026-05-27

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Re-verified robust backend and node tests properly pass after migrating to a direct SQL `UPDATE` statement in the `process_message` Celery task.
* **Upgrades:** Checked minor/patch bumps for dependencies. Checked dependencies safely. Bumped project versions to `1.0.28`.
* **Pruning:** Pruned `__pycache__` artifacts to maintain repository cleanliness and reduce entropy.

## [1.0.27] - 2026-05-26

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations introducing security bumps in the Node.js collector. Re-verified robust backend and node tests properly pass.
* **Upgrades:** Audited dependencies and safely bumped 8 Python dependencies (`idna`, `click`, `wrapt`, `httptools`, `huggingface-hub`, `sqlalchemy`, `kubernetes`, `posthog`) via Poetry. Verified Node.js dependencies are up to date.
* **Pruning:** Pruned `__pycache__` artifacts to maintain codebase entropy.

## [1.0.26] - 2026-05-21

* **Maintenance**: Assure lifecycle, prune entropy.
* **Dependencies**: Bumped `axios` and 19 minor python packages.
* **Performance**: Optimized DB object fetches with `load_only` in Celery workers.

## [1.0.25] - 2026-05-12

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations introducing direct SQL `UPDATE` queries in the Celery worker. Re-verified robust backend and node tests properly pass.
* **Upgrades:** Audited dependencies and safely bumped `python` dependencies via Poetry and Node.js dependencies via npm.
* **Pruning:** Pruned `__pycache__` directories to maintain codebase entropy. Addressed `vulture` static analysis warning in Pydantic validator by renaming unused `cls` variable to `_cls`.

## [1.0.24] - 2026-05-05

* **Lifecycle:** Evaluated that API latency is reduced using `ORJSONResponse` across endpoints as expected.
* **Lifecycle:** Pruned `__pycache__` artifacts to maintain repository cleanliness and reduce entropy.
* **Dependencies:** Bumped 15 Python dependencies to their latest minor/patch versions. Checked Node.js dependencies safely.

## [1.0.23] - 2026-05-05

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations introducing `GZipMiddleware` in the FastAPI backend for payload compression. Verified test suites and `vulture` static analysis appropriately pass.
* **Upgrades:** Checked dependencies via Poetry and Node.js. No newer patch versions found.
* **Pruning:** Pruned `__pycache__` directories to reduce codebase entropy.

## [1.0.21] - 2026-05-03

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations introducing index-based row mapping in FastAPI endpoints to eliminate dictionary allocation overhead. Re-verified test suites and `vulture` static analysis still pass.
* **Upgrades:** Audited dependencies and safely bumped `wcwidth` to `0.7.0` via Poetry in the Python backend. Verified Node.js dependencies are up-to-date.
* **Pruning:** Pruned `__pycache__` directories to maintain codebase entropy.

## [1.0.20] - 2026-05-01

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations introducing `ORJSONResponse` in the FastAPI backend for faster JSON serialization payloads. Verified test suites and `vulture` static analysis still pass.
* **Upgrades:** Audited dependencies across the platform. Applied safe minor/patch upgrades for Python dependencies (`fsspec`, `typer`, `huggingface-hub`, `posthog`). Verified Node packages are up-to-date.
* **Pruning:** Pruned `__pycache__` directories to maintain codebase entropy.

## [1.0.18] - 2026-04-28

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations ensuring robust handling of `undefined` message bodies in the node collector by applying a strict string fallback prior to Pydantic ingestion. Re-verified testing suites remain stable.
* **Upgrades:** Audited and applied safe patch version updates for backend dependencies via Poetry. Node.js dependencies are up to date.
* **Pruning:** Pruned unused `asyncio` import in `backend/app/main.py`. Removed `__pycache__` directories to reduce codebase entropy. Vulture static analysis cleanly reports no non-expected dead code.

## [1.0.17] - 2026-04-25

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations enforcing strict Pydantic validation (using `Literal`) for AI message analysis. Re-verified robust backend and node tests properly pass.
* **Upgrades:** Bumped patch version for node dependency `whatsapp-web.js` to `^1.34.7` and python backend dependencies via poetry update.
* **Pruning:** Pruned `__pycache__` artifacts to reduce codebase entropy.

## [1.0.16] - 2026-04-24

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations of database indexes (removing redundant primary key/composite indexes) and hardening Pydantic schemas against unbounded inputs. Verified database lookup queries use efficient `session.get()` bypassing redundant fetches. Tests correctly pass validating database queries and schemas.
* **Upgrades:** Audited minor/patch bumps. All backend (`pyproject.toml`) and collector (`package.json`) dependencies remain safely up to date.
* **Pruning:** Pruned `__pycache__` artifacts to reduce codebase entropy.

## [1.0.15] - 2026-04-23

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations that secured dashboard API endpoints and prevented circular dependencies by moving `get_api_key` to a dedicated `auth.py` module. Re-verified robust backend and node tests properly pass.
* **Upgrades:** Bumped patch version for python dependencies `certifi`, `idna`, `click`, `typer`, and `onnxruntime`. Node.js dependencies remain up to date.
* **Pruning:** Pruned `__pycache__` artifacts to reduce codebase entropy.

## [1.0.14] - 2026-04-22

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations of the hot path eliminating the redundant db.get read check on webhook ingestion. Verified robust passing tests for idempotent db.execute behavior in duplicate message cases.
* **Upgrades:** Bumped patch version for node dependency `axios` to `^1.15.2` and python dependencies `idna`, `posthog`, and `psycopg2-binary`.
* **Pruning:** Pruned `__pycache__` artifacts to reduce codebase entropy.

## [1.0.13] - 2026-04-20

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Re-verified robust backend and node tests properly pass.
* **Upgrades:** Bumped patch version for node dependency `axios` to `^1.15.1`, and python dependencies `pydantic`, `filelock`, and `pydantic-settings`. Bumped project versions to `1.0.13`.
* **Pruning:** Removed `__pycache__` artifacts to reduce codebase entropy.

## [1.0.12] - 2026-04-18

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations of standard SQL FILTER usage in the dashboard. The `COUNT(id) FILTER (WHERE ...)` query resolves silent 0-row coalescing correctly and remains performant.
* **Upgrades:** Checked minor/patch bumps for dependencies. Bumped version across projects to `1.0.12`.
* **Pruning:** Added comprehensive unit tests for dashboard endpoint `get_group_stats` covering active elements and empty records. Removed `__pycache__` artifacts to reduce codebase entropy.

## [1.0.11] - 2026-04-17

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations of silent error handling, split-brain transactions, and celery worker configurations. Verified all backend and collector test suites pass.
* **Upgrades:** Checked minor/patch bumps for python dependencies (updated pydantic/pydantic-core) and node packages (updated dotenv). Bumped version across projects to `1.0.11`.
* **Pruning:** Removed `__pycache__` artifacts to reduce codebase entropy.

## [1.0.10] - 2026-04-16

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Re-verified backend tests perfectly pass. Pruned `__pycache__` artifacts.
* **Upgrades:** Checked minor/patch bumps for python and node packages and bumped version across projects to `1.0.10`.

## [1.0.9] - 2026-04-09

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Re-verified backend tests completely pass.
* **Upgrades:** Checked minor/patch bumps for python and node packages and bumped version across projects to `1.0.9`.

## [1.0.8] - 2026-04-04

### Assure, Prune, and Sync
* **Code Pruning:** Eliminated unused async method `analyze_message` from AI engine, reducing technical debt and resolving static analysis warnings.

## [1.0.4] - 2026-03-31

### Assured & Pruned
* **Lifecycle:** Verified system integrity post-optimizations. Test suite passing (5/5 tests).
* **Code Pruning:** Eliminated unused compiled Python files (`__pycache__`) and scratch files to reduce entropy.

### Upgrades
* **Dependencies:** Bumped minor/patch version of `dotenv` to `^17.3.1` in Node.js Collector.

## [1.0.3] - 2026-03-30

### Assured & Pruned
* **Security:** Hardened API key validation by implementing `secrets.compare_digest` for secure, constant-time validation of `X-API-Key` headers, mitigating timing attack vectors.
* **Dependencies:** Bumped safe minor/patch dependencies across the Node.js Collector (`nodemon`) and Python backend.
* **Code Pruning:** Removed unused `JSON` module import from database models and eliminated obsolete scratch directories (`__pycache__`).

## [1.0.2] - 2026-03-29

### Assured & Pruned
* **Lifecycle:** Pruned dead code `topics` and `is_bot` from `backend/app/db/models.py`, `backend/app/ai/engine.py`, and `backend/app/workers/tasks.py`.
* **Dependencies:** Bumped safe minor/patch dependency `nodemon` to `^3.1.14` in Node.js Collector.

## [1.0.1] - 2024-05-18

### Assured & Pruned
* **Lifecycle:** Verified system integrity post-optimizations. Test suite passing (6/6 tests).
* **Code Pruning:** Eliminated unused database schema model `Summary` and its related `SummaryResponse`. Removed unreachable `search_similar_messages` logic from `chroma.py`, saving technical debt.

### Upgrades
* **Dependencies:** Bumped minor/patch versions of standard packages in the Node.js Collector (e.g., `axios`, `dotenv`, `nodemon`, `whatsapp-web.js`) and resolved minor vulnerabilities.
## [1.0.5] - 2026-04-01
### Assure, Prune, and Sync
* **Lifecycle:** Pruned dead variables and `topics` tracking from `seed.py`. Upgraded `dotenv` module to safe minor/patch versions across node dependencies. Consolidated print statements to use standard python `logging` modules in `engine.py` and `chroma.py`.

## [1.0.6] - 2026-04-02

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Re-verified backend tests perfectly pass.
* **Upgrades:** Bumped safe patch versions for python dependencies `aiohttp` and `charset-normalizer`.

## [1.0.7] - 2026-04-03

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Pruned `__pycache__` artifacts to reduce codebase entropy. Verified static analysis with no dead code found.
* **Upgrades:** Bumped safe minor/patch versions for node dependency `dotenv` and multiple python backend dependencies (`click`, `orjson`, `huggingface-hub`, `sqlalchemy`, etc).

### Assure, Prune, and Sync
* **Lifecycle:** Resolved asyncio event loop blocking in `seed.py` by offloading `ai_engine.analyze_message_sync` to `asyncio.to_thread`.
* **Pruning:** Added `.vulture_whitelist.py` in the backend to prune static analysis false positives on FastAPI endpoints and Celery tasks, achieving a zero-warning vulture run.

## [Unreleased]
**Fixed:** Resolved a data consistency bug in the Celery worker by ensuring the vector embedding network upload happens atomically within the database transaction boundary.
**Assurance:** Verified system integrity post-optimizations. Deferred NPM vulnerability fixes in the Node.js Collector (`extract-zip`, `tar-fs`, `ws`, `zod`, `basic-ftp`) due to breaking major version constraints.

## [Unreleased]
**[Fixed]:** Sanitized database connection string secrets from being leaked into internal application error logs.

## [Unreleased]
**[Fixed]:** Resolved moderate security vulnerabilities in nested NPM dependencies (`glob` and `minimatch`) within the Node.js Collector by updating package overrides.

## [Unreleased]
**[Pruned]:** Removed unused `lucide-react` dependency from frontend.
