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

**283 tests: 218 unit, 65 integration | 64% overall | ~96% testable layer**

The overall 64% includes `app/ingestion/`, `app/enrichment/` and `app/scheduler.py` which are intentionally excluded (live HTTP to external ATSes / Wikipedia/Wikidata). The testable layer (routers, normalizer, schemas, config) sits at ~96%.

## Files

### Unit

| File                         | Tests | Covers                                                                            |
| ---------------------------- | ----- | --------------------------------------------------------------------------------- |
| [unit/test_text.py](unit/test_text.py)                   | 12    | `strip_html`, `make_snippet`                                                      |
| [unit/test_location.py](unit/test_location.py)           | 51    | `canonicalize_city`, `normalize_location`, `get_region_for_country`               |
| [unit/test_pagination.py](unit/test_pagination.py)       | 3     | `_decode_cursor` (error paths)                                                    |
| [unit/test_filters.py](unit/test_filters.py)             | 11    | `JobFilters` parsing, capping, and `without()`                                    |
| [unit/test_classifiers.py](unit/test_classifiers.py)     | 73    | `classify_seniority`, `classify_role`, `extract_tech_stack`, `normalize_job_type` |
| [unit/test_ingesters.py](unit/test_ingesters.py)         | 48    | `build_job`, `extract_job_id`, and job_type vocabulary per ATS                     |
| [unit/test_ingest_flow.py](unit/test_ingest_flow.py)     | 10    | Dedup, hydration split, and soft-deactivation in `BaseIngester`                   |
| [unit/test_payments.py](unit/test_payments.py)           | 10    | `create_order` (validation), `verify_payment` (HMAC)                              |

### Integration

| File                            | Tests | Covers                                                           |
| ------------------------------- | ----- | ---------------------------------------------------------------- |
| [integration/test_health.py](integration/test_health.py)       | 2     | `/health`, `/`                                                   |
| [integration/test_jobs.py](integration/test_jobs.py)           | 23    | `/jobs`, `/jobs/facets`, `/jobs/{id}`                            |
| [integration/test_search.py](integration/test_search.py)       | 9     | `/search`                                                        |
| [integration/test_companies.py](integration/test_companies.py) | 10    | `/companies`, `/companies/{slug}`, `/companies/{slug}/jobs`      |
| [integration/test_cities.py](integration/test_cities.py)       | 5     | `/cities`, `/cities/{slug}`                                      |
| [integration/test_map.py](integration/test_map.py)             | 12    | `/map/companies`, `/map/cities`, `/map/companies/{slug}/offices` |
| [integration/test_stats.py](integration/test_stats.py)         | 4     | `/stats`                                                         |
