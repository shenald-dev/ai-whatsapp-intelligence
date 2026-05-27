## 2026-05-26 — Prevent cache TTL vulnerability from system clock adjustments

* **What changed:** Replaced `time.time()` with `time.monotonic()` for TTL expiration calculations in the `BoundedTTLCache` within `backend/app/api/endpoints.py`.
* **Why it matters:** Using `time.time()` is vulnerable to system clock adjustments (like NTP synchronizations or leap seconds), which can cause premature cache invalidation or artificially extend the TTL of stale data. `time.monotonic()` guarantees a strictly forward-moving clock, ensuring reliable duration tracking.
* **How it was verified:** Verified by successfully running the backend test suite (`pytest`) and the collector test suite (`npm test`). Also requested an autonomous code review, ensuring it passed correctly without any unneeded dependency changes.
* **Remaining risk:** Negligible. This is a standard and robust replacement for measuring time durations in Python.
* **Commit Result:** Committed with message `fix(cache): use time.monotonic() for reliable TTL calculation` and tagged as `v1.0.27`.
