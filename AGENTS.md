# Repository Guidelines

## Project Structure & Module Organization
This repository is a small FastAPI + FFmpeg service.

- `src/app.py`: API entrypoint (`/api/hls_start`, `/api/hls_stop`, `/ws`) and lifecycle tasks.
- `src/record.py`: recording process orchestration (`RecordManager`) and disk-space safeguards.
- `src/save_hls.py`: standalone CLI recorder/converter script.
- `src/tos_client.py`: TOS upload wrapper.
- `src/testtos.py`: manual connectivity script (not an automated test).
- `pyproject.toml`: dependencies, packaging, and pytest settings.
- `Dockerfile`: production image build and runtime command.

## Build, Test, and Development Commands
Run commands from repository root (`hocky_hls/`).

- `python -m pip install -e .` installs the service in editable mode.
- `python -m pip install -e ".[dev,test]"` installs lint/test extras (`ruff`, `pytest`, `httpx`).
- `uvicorn app:app --app-dir src --reload --host 0.0.0.0 --port 8000` starts local API dev server.
- `python -m pytest -q` runs tests configured in `pyproject.toml`.
- `ruff check src` runs lint checks.
- `docker build -t hocky-hls .` builds the container image.

## Coding Style & Naming Conventions
- Use Python 3.11+ and 4-space indentation.
- Prefer PEP 8 naming: `snake_case` for functions/variables, `PascalCase` for classes.
- Keep modules focused: API logic in `app.py`, recording logic in `record.py`.
- Add type hints for new/changed public functions where practical.
- Use `ruff` before opening a PR.

## Testing Guidelines
- Use `pytest` for new tests; place them under `tests/` with filenames like `test_record.py`.
- Test API behavior with FastAPI test clients and core logic in `RecordManager`.
- Keep tests deterministic; mock FFmpeg/subprocess calls when possible.
- Run `python -m pytest -q` before each PR.

## Commit & Pull Request Guidelines
Git history is not available in this workspace, so no existing commit convention could be inferred. Use this standard:

- Commit format: `type(scope): short summary` (for example: `fix(record): handle stale m3u8`).
- Keep commits focused and atomic.
- PRs should include: purpose, behavior changes, test evidence, and config/env updates.
- Link related issues and include API request/response examples for endpoint changes.

## Security & Configuration Tips
- Never commit real credentials or tokens. `src/testtos.py` currently contains hardcoded secrets and should be migrated to environment variables.
- Validate external paths and inputs passed to FFmpeg/TOS operations.
