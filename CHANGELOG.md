# Changelog

All notable changes to this project will be documented in this file.

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