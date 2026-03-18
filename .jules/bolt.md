## 2025-05-15 — Enforced Fail-Fast for Sensitive Credentials

Learning: Hardcoded credential fallbacks in environment variable lookups (e.g., `os.getenv("DATABASE_URL", "...")`) create a security risk where applications might silently use default, insecure credentials if the environment is misconfigured.

Action: Replaced all instances of `os.getenv` for sensitive credentials (DATABASE_URL, SYNC_DATABASE_URL, REDIS_URL, API_KEY) with explicit `os.environ.get` checks that raise `ValueError` or `HTTPException` if the variable is missing. Added a `verify_fix.py` script to automate this check across the backend.
