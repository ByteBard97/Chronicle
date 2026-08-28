.PHONY: test lint sim check check-dashboard

test:
	uv run pytest

lint:
	uv run ruff check .

sim:
	uv run python -m chronicle

check-dashboard:
	cd dashboard && npm run build && npm test && npm run check-range

# Full acceptance battery: sim tests + lint + dashboard build/tests/Range.
# Run `npm run visual-diff` separately when the map view changes (heavier).
check: test lint check-dashboard

# Live-game suite: launches ChronicleDev + DevBench, drives every ChronicleBridge slice
# unattended (docs/design/live-test-harness.md). Never part of `make check`.
live-check:
	CHRONICLE_LIVE=1 uv run --with pydantic --with pytest pytest adapters/skyrim/livetest -rA -x -p no:cacheprovider
