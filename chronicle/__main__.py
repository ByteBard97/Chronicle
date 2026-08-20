"""Headless entry point. Currently a stub — the tick loop lands with the engine."""

from chronicle.events import EventLog


def main() -> None:
    log = EventLog()
    print(f"chronicle: event log initialized, {len(log.all())} events")


if __name__ == "__main__":
    main()
