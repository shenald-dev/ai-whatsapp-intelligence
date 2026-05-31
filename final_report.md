## Improvements Made
- Replaced `func.count(models.Message.id)` with `func.count()` in `get_group_stats` API endpoint.

## Why It Matters
Using `func.count(Column)` in SQLAlchemy checks for `NULL` values before counting, adding unnecessary overhead. Using `func.count()` simply counts the rows (`COUNT(*)`), resulting in faster database execution on this frequently hit analytics endpoint. This will reduce overall API latency and DB CPU load.

## How It Was Verified
- `pytest` for backend tests.
- `npm test` for collector tests.
- Locally reviewed the SQL emitted with `postgresql.dialect()` via a scratchpad to ensure the output shifted from `COUNT(messages.id)` to `COUNT(*)`.

## Remaining Risk
None. The optimization strictly reduces DB overhead while providing the exact same count given the nature of the table structure.
