"""Sync check between the two sides of the Whiterun named-cast growth pass.

adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp's kNamedCast table and
chronicle/fixtures/whiterun_schedule.py's whiterun_schedule() are hand-kept
in sync by convention, not by any shared source of truth (Python can't
parse the C++ file). This test hardcodes the chronicleNpcId values added to
kNamedCast on 2026-08-26 and asserts each one appears as an npc_id in
whiterun_schedule()'s output, so a future edit to one side that forgets the
other is caught immediately instead of silently going stale.
"""

from __future__ import annotations

from chronicle.fixtures.whiterun_schedule import whiterun_schedule

# Mirrors adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp's kNamedCast
# table exactly (chronicleNpcId column), including the pre-existing
# "ysolda" entry.
NAMED_CAST_NPC_IDS = frozenset(
    {
        "ysolda",
        "idolaf_battle_born",
        "saffir",
        "carlotta_valentia",
        "amren",
        "adrianne_avenicci",
        "lars_battle_born",
        "braith",
        "fralia_gray_mane",
        "nazeem",
        "lillith_maiden_loom",
        "brenuin",
        "anoriath",
        "lucia",
        "heimskr",
        "sigurd",
        "olava_the_feeble",
        "danica_pure_spring",
        "olfina_gray_mane",
    }
)


def test_named_cast_npc_ids_all_have_a_schedule_block():
    """Every IdentityMap.cpp kNamedCast entry must be schedulable in Chronicle."""
    scheduled_npc_ids = {block.npc_id for block in whiterun_schedule()}
    missing = NAMED_CAST_NPC_IDS - scheduled_npc_ids
    assert not missing, f"kNamedCast npc_ids with no whiterun_schedule() block: {sorted(missing)}"
