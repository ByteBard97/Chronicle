"""Keyed randomness -- the sim's single dice-roll choke point (ADR-0009).

Every random draw in the sim is a pure function of an explicit key; there is
no sequential stream state anywhere. Replay is exact (same seed_id + same
inputs => same keys => same values), and fork divergence is analyzable: two
generations differ exactly at keys whose inputs differ, which is what the
frame-log merge-scan first-divergent-roll finder (ui-spec §3.9) compares.

The roll key's six members (order owned by docs/decisions/0009-keyed-
randomness.md; cited by docs/frame-log-schema.md §4, for which changing this
encoding is a schema break):

  - seed_id      -- the run's statistical identity;
  - purpose      -- the roll site's registered string (PURPOSES below);
  - tick         -- the current tick (ADR-0010: 1 tick = 1 game-hour);
  - site         -- the location id, or a scoped non-location string for
                    non-spatial rolls (e.g. the claim id for mutation rolls);
  - participants -- the sorted, order-normalized entity ids involved;
  - draw         -- a 0-based discriminator distinguishing multiple rolls in
                    an otherwise identical context.

Implementation: SHA-256 over the canonical serialization
``seed_id | purpose | tick | site | participants(comma-joined) | draw``,
first 8 bytes as uint64, divided by 2**64. SHA-256 truncation is
statistically adequate at our roll volumes (<=10^6 rolls/run) and needs no
dependency; counter-based PRNGs (Philox/Threefry) were considered and
rejected as unnecessary today -- this module is the seam a future primitive
swap lands behind without changing call sites (ADR-0009).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

# Purposes are a registry (ADR-0009 §2): each roll site gets a dotted purpose
# string defined once here -- no ad-hoc purpose strings at call sites. The
# initial set matches docs/frame-log-schema.md §4; mutation/tell-decision
# sites are Tier 2/3 machinery that lands later, registered now so the
# vocabulary can't drift.
ENCOUNTER_CO_PRESENCE = "encounter.co-presence"  # schedule sampling (chronicle/schedule.py)
MUTATION_SLOT = "mutation.slot"  # Tier 2: which slot a retelling mutates
MUTATION_VALUE = "mutation.value"  # Tier 2: what value the mutation substitutes
TELL_DECISION = "tell.decision"  # Tier 3: whether a teller chooses to tell at all

PURPOSES = frozenset({ENCOUNTER_CO_PRESENCE, MUTATION_SLOT, MUTATION_VALUE, TELL_DECISION})


def roll_key(
    *,
    seed_id: str,
    purpose: str,
    tick: int,
    site: str,
    participants: Sequence[str],
    draw: int,
) -> dict[str, object]:
    """The trace-record form of a roll key (frame-log schema §4): the six members, participants order-normalized."""
    if purpose not in PURPOSES:
        raise ValueError(f"purpose {purpose!r} is not in the registered PURPOSES -- roll sites register their purpose in chronicle/rng.py (ADR-0009 §2)")
    return {
        "seed_id": seed_id,
        "purpose": purpose,
        "tick": tick,
        "site": site,
        "participants": sorted(participants),
        "draw": draw,
    }


def _canonical(key: dict[str, object]) -> bytes:
    """The canonical serialization ADR-0009 pins: pipe-joined members, participants comma-joined."""
    return "|".join(
        [
            str(key["seed_id"]),
            str(key["purpose"]),
            str(key["tick"]),
            str(key["site"]),
            ",".join(key["participants"]),  # type: ignore[arg-type]  # already sorted by roll_key()
            str(key["draw"]),
        ]
    ).encode("utf-8")


def roll(
    *,
    seed_id: str,
    purpose: str,
    tick: int,
    site: str,
    participants: Sequence[str],
    draw: int,
) -> float:
    """One keyed roll: uniform in [0, 1), a pure function of its key.

    participants are order-normalized (sorted) inside the key, so
    roll(participants=("b", "a")) == roll(participants=("a", "b")) -- an
    encounter between two NPCs is the same roll regardless of which one the
    caller happened to list first.
    """
    key = roll_key(seed_id=seed_id, purpose=purpose, tick=tick, site=site, participants=participants, draw=draw)
    digest = hashlib.sha256(_canonical(key)).digest()
    return int.from_bytes(digest[:8], "big") / 2**64
