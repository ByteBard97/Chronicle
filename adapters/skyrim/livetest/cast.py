"""Runtime reference FormIDs for the named cast in the ChronicleDev load order.

Observed live via DevBench ``inspect refs formType=Actor`` on 2026-08-28
(HearthFires.esm is load index 03 in this instance). These are *reference*
ids (the placed ACHR), which is what ``prid``, ``player.moveto`` and Papyrus
``self`` need -- not the NPC_ base ids ``IdentityMap.cpp`` lists.
"""

from __future__ import annotations

REFS: dict[str, str] = {
    "nazeem": "0x0001A6A4",
    "ysolda": "0x0001A69A",
    "brenuin": "0x0002C90F",
    "fralia_gray_mane": "0x0001A684",
    "olfina_gray_mane": "0x0001A685",
    "idolaf_battle_born": "0x0001A689",
    "lars_battle_born": "0x0001A68C",
    "carlotta_valentia": "0x0001A675",
    "lucia": "0x03003F5E",
    "amren": "0x0001A66A",
    "saffir": "0x0001A66C",
    "sigurd": "0x000CDD73",
    "adrianne_avenicci": "0x0001A67C",
    "anoriath": "0x0001A680",
    "heimskr": "0x0001A682",
    "braith": "0x0001A66B",
    "lillith_maiden_loom": "0x0010E2B6",
}

PLAYER = "0x00000014"

# Candidate pairs for hydration's "does an authored vanilla BGSRelationship
# exist?" sweep -- family/household pairs first (runbook §3).
HYDRATION_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("fralia_gray_mane", "olfina_gray_mane"),
    ("idolaf_battle_born", "lars_battle_born"),
    ("carlotta_valentia", "lucia"),
    ("amren", "saffir"),
    ("sigurd", "adrianne_avenicci"),
)

EVIDENCE_ITEM_NAME = "Chronicle Evidence"
