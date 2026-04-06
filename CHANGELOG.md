# Changelog

All notable changes to this project will be documented in this file.

## [1.0.7] - 2026-04-03

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Ensured robust exception handling for database operations during webhook ingestion by aligning the UPSERT logic within the primary transaction block. Re-verified all tests pass.
* **Code Pruning:** Addressed Vulture warnings by asserting on the mock in the unit tests and pruned codebase of transient `__pycache__` artifacts to reduce entropy.
* **Upgrades:** Safely bumped minor and patch versions for Node.js (`dotenv`) and Python backend dependencies.

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
