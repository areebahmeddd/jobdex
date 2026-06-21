# Contributing

Thanks for your interest in contributing to JobDex. This guide covers conventions, testing, and the pull request process.

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Setup

For prerequisites and local setup, refer to the service-specific READMEs:

- [backend/README.md](../backend/README.md)
- [frontend/README.md](../frontend/README.md)

For a full-stack environment, run from the repository root:

```bash
docker compose up --build
```

## Code Conventions

**Backend (Python)**

Formatting and linting are handled by [ruff](https://docs.astral.sh/ruff/). Run before committing:

```bash
uv run ruff check .
uv run ruff format .
```

- Follow the existing SQLAlchemy `Mapped[]` style for model definitions.
- Keep business logic out of routers. Routers build responses; ingestion and enrichment logic live in their own modules.
- New ingestion sources must subclass `BaseIngester` and implement `fetch_raw`, `extract_job_id`, and `build_job`.

**Frontend (TypeScript)**

- Use named exports for components.
- Keep map-specific logic in `features/map/`. Landing page content goes in `features/landing/`.
- Shared UI primitives belong in `components/ui/`.

## Testing

**Backend:**

```bash
cd backend
uv run pytest
```

Integration tests require a live database connection via `DATABASE_URL`. Unit tests in `tests/unit/` run without one. New code should include tests where applicable.

## Branching

- `main` is the stable branch.
- Use `feature/{short-description}` for new work and `fix/{short-description}` for bug fixes.
- Keep commits focused. One logical change per commit.

## Pull Requests

1. Fork the repository and create your branch from `main`.
2. Make your changes and ensure the test suite passes.
3. Run the linter before committing.
4. Open a pull request with a clear title and a description of what changed and why.
5. Reference any related issue with `Closes #NNN`.

## Sign-off

All commits must include a `Signed-off-by` trailer. Use `git commit -s` to add it automatically:

```
Signed-off-by: Your Name <your@email.com>
```

This certifies that you agree to the [Developer Certificate of Origin](https://developercertificate.org): that you wrote the contribution or have the right to submit it under this project's license.
