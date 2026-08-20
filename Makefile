.PHONY: test lint sim

test:
	uv run pytest

lint:
	uv run ruff check .

sim:
	uv run python -m chronicle
