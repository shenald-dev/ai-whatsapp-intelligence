## APEX FORGE Run Report

**What changed:**
Replaced `time.time()` with `time.monotonic()` in the `BoundedTTLCache` implementation inside `backend/app/api/endpoints.py` to calculate Time-To-Live (TTL) cache expirations reliably. Also bumped version to `1.0.27` across `pyproject.toml`, `package.json`, and `main.py`, updated lockfiles, and logged the learning in `.jules/bolt.md`.

**Why it matters:**
`time.time()` uses the system wall clock, which is subject to adjustments (e.g., NTP syncing), causing the clock to occasionally leap forward or backward. This can result in premature cache invalidation or artificially extended TTLs. `time.monotonic()` is unaffected by system clock adjustments and guarantees monotonically increasing time values, providing robust and predictable cache behavior. This improves API reliability and ensures accurate TTL performance.

**What was measured or how the improvement is justified:**
The improvement was identified structurally as a known unreliability pattern. No specific performance metrics were necessary, but the structural correctness and reliability of the internal cache eviction logic are enhanced without overhead.

**What checks were run:**
- Verified code changes directly with `read_file`.
- Python tests: Executed `pytest` in `backend`, covering `test_chroma`, `test_cors`, `test_dashboard`, `test_db`, `test_ingest`, and `test_workers` (19 items passed).
- Node.js tests: Executed `npm test` in `collector` (4 subtests passed).
- Ran automated static code review, confirming correct resolution of the TTL logic flaw.

**Repository Status:**
Ready. The repository is verified, tests pass, and it's tagged as version `v1.0.27`.

**Remaining Limitation or Risk:**
None. The change is extremely localized and backward compatible since `time.monotonic()` yields seconds as a float, just like `time.time()`.
