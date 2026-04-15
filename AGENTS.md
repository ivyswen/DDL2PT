# Repository Guidelines

## Project Structure & Module Organization

This repository is a PySide6 desktop tool that converts `ALTER TABLE` SQL into `pt-online-schema-change` commands.

- `main.py`: app entry point, initializes Qt app and main window.
- `core/`: conversion logic (`converter.py`) and parameter model (`PTConfig`).
- `ui/`: UI composition (`main_window.py`), theme (`style.py`), and runtime icons (`ui/icons/`).
- `Resources/`: packaged app assets (favicon/app icon).
- `build_nuitka.py`: Windows packaging script (Nuitka).
- `build/`: generated packaging output (do not edit manually).

Keep business logic in `core/` and keep UI event wiring in `ui/`.

## Build, Test, and Development Commands

- `uv sync`: install runtime and dev dependencies from `pyproject.toml`/`uv.lock`.
- `uv run python main.py`: launch the desktop app locally.
- `python main.py`: alternative run command if you do not use `uv`.
- `uv run python build_nuitka.py`: build a distributable Windows executable.
- `pip install nuitka ordered-set zstandard`: required once before packaging (if not using `uv`).

## Coding Style & Naming Conventions

- Python 3.11+, 4-space indentation, UTF-8 encoding.
- Prefer type hints (`def func(...) -> str`) for new or changed functions.
- Naming: `snake_case` for functions/variables/modules, `PascalCase` for classes, `UPPER_CASE` for constants.
- Keep comments concise and meaningful; avoid restating obvious code.
- UI text is Chinese-first in this project; keep terminology consistent with existing labels.

## Testing Guidelines

There is currently no committed automated test suite. For new logic:

- Add unit tests under `tests/` (e.g., `tests/test_converter.py`).
- Use `pytest` naming (`test_*.py`, `test_*` functions).
- Prioritize `core/converter.py` parsing and command-assembly edge cases.
- Before PR, at minimum run a manual smoke test: `uv run python main.py` and verify conversion/copy/reset flows.

## Commit & Pull Request Guidelines

Git history is not established yet, so use Conventional Commits going forward:

- Examples: `feat(core): support quoted schema names`, `fix(ui): preserve settings on close`.
- Keep commits focused and reversible; avoid mixing UI refactor with converter logic changes.
- PRs should include: purpose, key changes, manual test steps, and screenshots/GIFs for UI changes.
- Link related issue IDs when applicable and note any packaging-impacting changes (`build_nuitka.py`, `Resources/`).
