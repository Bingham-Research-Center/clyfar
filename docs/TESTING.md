# Testing Primer (pytest)

This repo uses pytest for lightweight, fast tests. Start small and keep tests deterministic (no network, no large downloads).

## Setup & Running
- Install: `pip install pytest`
- Run all tests: `pytest`
- Quiet mode / subset: `pytest -q`, `pytest -k utils`
- Test layout: place files under `tests/` named `test_*.py`; write functions `def test_*():`.

## Writing Good Tests
- Keep them focused (one behavior per test) and fast (<100ms where possible).
- Use pure, in-memory data. Avoid network, file I/O, and global state.
- Prefer explicit assertions (`assert result == expected`).
- Skip heavy dependencies when absent: `pytest.importorskip("xarray")`.
- Use built-in fixtures like `tmp_path` for temporary files/dirs.

## Examples
- Utilities: see `tests/test_utils.py` for date/time helpers and selectors.
- Lookups: see `tests/test_lookups.py` for synonym resolution.
- DataFrame shaping: see `tests/test_preprocessing_dataframe.py` for `create_forecast_dataframe`.

## Conventions
- One-liner docstring or comment per non-obvious test.
- Name tests by behavior: `test_<function>_<case>()`.
- Group related tests in the same file; split when the file grows too large.

## Working With Codex Agents
- Be explicit about goals: “Add pytest for utils and lookups; no network.”
- Ask for a plan first (files to add, targets to test, any skips/mocks).
- Request minimal, fast tests with clear assertions and example commands to run.
- Share failures verbatim; ask for focused fixes (don’t refactor unrelated code).
- Encourage agents to add `pytest.ini` and use `pytest -q` for quick iteration.

With this in place, you can iteratively grow coverage while keeping the feedback loop fast and reliable.
