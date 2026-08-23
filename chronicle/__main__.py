"""Headless entry point: ``python -m chronicle <subcommand> ...``.

Subcommand logic lives in ``chronicle/cli.py`` (docs/dashboard-build-plan.md
§2 M1's agent-debug CLI) -- ``inspect``/``trace``/``feed`` are read-only
views over a run's frame log via ``chronicle/framelog.py``'s
``FrameLogReader``; ``inject`` composes and validates canonical-event JSON
without writing to a run's log.
"""

import sys

from chronicle.cli import run


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
