"""Turns a sampled encounter (chronicle.schedule) into rumor propagation (chronicle.claims).

This is the "math tier" glue docs/architecture.md describes as running
every tick over all NPCs: chronicle.schedule decides who could plausibly
have talked to whom this tick; chronicle.claims decides what a retelling
does once it happens. This module is deliberately thin -- it only
decides, given an encounter and the store's current beliefs, whether
there is anything to propagate at all.

Not every encounter propagates something: if neither party holds a
belief about a given claim, or both already do, there's nothing this
encounter changes for that claim (rule 2's "sampled encounter", not "an
encounter always produces a retelling"). teller_and_hearer() is the
one-shot check a caller makes before deciding to call ClaimStore.retell()
-- it does not call retell() itself, since retell() also needs a mutation
decision (rule 3) and fresh id generation that belong to the caller
running the actual tick loop, not to this lookup.
"""

from __future__ import annotations

from chronicle.claims import ClaimStore


def teller_and_hearer(claims: ClaimStore, *, claim_id: str, npc_a: str, npc_b: str) -> tuple[str, str] | None:
    """Given an encounter between npc_a and npc_b, who (if anyone) could tell whom about claim_id.

    Returns (teller_id, hearer_id) only when exactly one of the pair
    already holds a belief about claim_id -- both holding one (nothing
    new to say) or neither holding one (this encounter isn't about that
    claim at all) both return None.
    """
    a_belief = claims.belief_of(npc_a, claim_id)
    b_belief = claims.belief_of(npc_b, claim_id)
    if a_belief is not None and b_belief is None:
        return npc_a, npc_b
    if b_belief is not None and a_belief is None:
        return npc_b, npc_a
    return None
