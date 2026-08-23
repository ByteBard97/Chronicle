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
running the actual tick loop, not to this lookup. Its both-informed twin,
conflicting_pair(), decides the ladder-T2.3 question: when both parties
already hold beliefs, whether their content differs enough to resolve.
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


def conflicting_pair(claims: ClaimStore, *, claim_id: str, npc_a: str, npc_b: str) -> tuple[str, str] | None:
    """Given an encounter where both parties hold beliefs about claim_id, who tells whom when their content differs.

    Returns (teller_id, hearer_id) only when both hold a belief about
    claim_id AND the slot content they hold differs (variant slots, or the
    claim's own slots for a witness's un-varianted original telling -- an
    eyewitness and the holder of an unmutated retelling of their story are
    NOT in conflict). Same content, or not both informed, returns None; the
    same-content case stays nothing_salient/"both-informed" and the encounter
    path performs no corroboration (coordinator ruling 2026-08-23).

    Direction is deterministic -- the lexicographically smaller npc id tells.
    A placeholder until a dialogue-direction policy exists; determinism, not
    a roll, is what replay needs (ADR-0009 -- no new RNG purpose for T2.3).
    """
    a_belief = claims.belief_of(npc_a, claim_id)
    b_belief = claims.belief_of(npc_b, claim_id)
    if a_belief is None or b_belief is None:
        return None
    if claims.held_slots(a_belief) == claims.held_slots(b_belief):
        return None
    return (npc_a, npc_b) if npc_a < npc_b else (npc_b, npc_a)
