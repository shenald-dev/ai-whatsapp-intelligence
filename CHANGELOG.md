# Changelog

All notable changes to this project will be documented in this file.

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
