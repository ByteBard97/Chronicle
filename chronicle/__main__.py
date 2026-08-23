"""Headless entry point: ``python -m chronicle <subcommand> ...``.

Subcommand logic lives in ``chronicle/cli.py`` (docs/dashboard-build-plan.md
§2 M1's agent-debug CLI) -- ``inspect``/``trace``/``feed`` are read-only
views over a run's frame log via ``chronicle/framelog.py``'s
``FrameLogReader``; ``inject <run_id> --event '<json>'`` appends one
canonical event to a run's events.jsonl (refusing historical ticks -- fork
territory, build plan §3), while ``inject --run ... --type ...`` composes
and validates the JSON the dashboard's injection console displays, without
writing.
"""

import sys

from chronicle.cli import main as _cli_main


def main() -> int:
    return _cli_main()


if __name__ == "__main__":
    sys.exit(main())
