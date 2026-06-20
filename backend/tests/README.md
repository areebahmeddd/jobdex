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

**130 tests -- 83 unit, 47 integration | 63% line coverage**

## Files

### Unit

| File                       | Tests | Covers                                                                            |
| -------------------------- | ----- | --------------------------------------------------------------------------------- |
| `unit/test_classifiers.py` | 42    | `classify_seniority`, `classify_role`, `extract_tech_stack`, `normalize_job_type` |
| `unit/test_location.py`    | 29    | `canonicalize_city`, `get_region_for_country`, `is_blocked_location`              |
| `unit/test_text.py`        | 12    | `strip_html`, `make_snippet`                                                      |

### Integration

| File                            | Tests | Covers                                                           |
| ------------------------------- | ----- | ---------------------------------------------------------------- |
| `integration/test_jobs.py`      | 9     | `/jobs`, `/jobs/{id}`                                            |
| `integration/test_map.py`       | 9     | `/map/companies`, `/map/cities`, `/map/companies/{slug}/offices` |
| `integration/test_cities.py`    | 8     | `/cities`, `/cities/{slug}`                                      |
| `integration/test_companies.py` | 8     | `/companies`, `/companies/{slug}`, `/companies/{slug}/jobs`      |
| `integration/test_search.py`    | 5     | `/search`                                                        |
| `integration/test_health.py`    | 4     | `/health`, `/`                                                   |
| `integration/test_stats.py`     | 4     | `/stats`                                                         |

## Not Covered

| Area               | Reason                          |
| ------------------ | ------------------------------- |
| `app/ingestion/`   | Live HTTP to external ATSes     |
| `app/enrichment/`  | Live HTTP to Wikipedia/Wikidata |
| `app/scheduler.py` | No unit-testable surface        |

## Stack

| Package                                                                | Version     | Purpose                        |
| ---------------------------------------------------------------------- | ----------- | ------------------------------ |
| [pytest](https://docs.pytest.org)                                      | 9.1         | Test runner                    |
| [pytest-cov](https://pytest-cov.readthedocs.io)                        | 7.1         | Coverage reporting             |
| [starlette TestClient](https://fastapi.tiangolo.com/tutorial/testing/) | via fastapi | In-process ASGI test transport |
