## 2026-05-26 — Prevent cache TTL vulnerability from system clock adjustments

Learning:
Using `time.time()` for cache Time-To-Live (TTL) calculations is vulnerable to system clock adjustments (like NTP syncs), which can lead to premature cache invalidation or artificially extended TTLs.

Action:
Always use `time.monotonic()` instead of `time.time()` for reliable duration and timeout calculations, as it is immune to system clock changes.