# Tests

## Commands

```bash
uv run pytest                                            # all
uv run pytest tests/unit                                 # no DB
uv run pytest tests/integration                          # requires DATABASE_URL
uv run pytest -m "not integration"                       # skip integration
uv run pytest --cov=app --cov-report=term-missing        # coverage (all tests)
uv run pytest --tb=short -q                              # quiet
```

## Coverage

**176 tests — 133 unit, 43 integration | 57% overall | ~92% testable layer**

The overall 57% includes `app/ingestion/`, `app/enrichment/`, and `app/scheduler.py` which are intentionally excluded (live HTTP to external ATSes / Wikipedia/Wikidata). The testable layer (routers, normalizer, schemas, config) sits at ~92%.

## Files

### Unit

| File                         | Tests | Covers                                                                            |
| ---------------------------- | ----- | --------------------------------------------------------------------------------- |
| `unit/test_classifiers.py`   | 71    | `classify_seniority`, `classify_role`, `extract_tech_stack`, `normalize_job_type` |
| `unit/test_location.py`      | 35    | `canonicalize_city`, `normalize_location`, `get_region_for_country`               |
| `unit/test_payments.py`      | 10    | `create_order` (validation), `verify_payment` (HMAC)                              |
| `unit/test_text.py`          | 12    | `strip_html`, `make_snippet`                                                      |
| `unit/test_pagination.py`    | 5     | `_encode_cursor`, `_decode_cursor`                                                |

### Integration

| File                            | Tests | Covers                                                           |
| ------------------------------- | ----- | ---------------------------------------------------------------- |
| `integration/test_jobs.py`      | 10    | `/jobs`, `/jobs/{id}`                                            |
| `integration/test_map.py`       | 9     | `/map/companies`, `/map/cities`, `/map/companies/{slug}/offices` |
| `integration/test_companies.py` | 7     | `/companies`, `/companies/{slug}`, `/companies/{slug}/jobs`      |
| `integration/test_search.py`    | 6     | `/search`                                                        |
| `integration/test_cities.py`    | 5     | `/cities`, `/cities/{slug}`                                      |
| `integration/test_stats.py`     | 4     | `/stats`                                                         |
| `integration/test_health.py`    | 2     | `/health`, `/`                                                   |

## Stack

| Package                                                                | Version     | Purpose                        |
| ---------------------------------------------------------------------- | ----------- | ------------------------------ |
| [pytest](https://docs.pytest.org)                                      | 9.1         | Test runner                    |
| [pytest-cov](https://pytest-cov.readthedocs.io)                        | 7.1         | Coverage reporting             |
| [starlette TestClient](https://fastapi.tiangolo.com/tutorial/testing/) | via fastapi | In-process ASGI test transport |
