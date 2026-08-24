# Lane 33 delivery report — Tier 4a design prep (schedule write-back)

**Delivered:** `d93c1b8` — `docs/design/tier-4a-schedule-write-back.md`.
No code. Suite unchanged: 206 passed, ruff clean (verified after writing
the doc, since a design lane shouldn't touch anything that could
regress it, and didn't).

## Cover note

**Decided** (this doc's own recommendations, ready to build against):

- Overlay, not mutation, for the write-back mechanism — and as a
  byproduct, fixes a latent schedule-reconstruction gap in
  `framelog.py` (the keyframe-tick-covers filter + `state_at` never
  replaying schedule between keyframes) that's been silently relying on
  the schedule being static since M0. This was the single most load-
  bearing finding: mutation would have turned a harmless gap into an
  active one exactly where T4a's own rungs probe.
- The roll-identity guarantee (T4a.2's core claim) needs **no new
  mechanism** — it's a direct consequence of how `sample_encounters`
  already computes each pair's roll independently of the rest of the
  occupancy list. The design work was proving it precisely and naming
  the exact assertion wording (per-pair, not per-site) plus the one
  precondition (an overlay must never touch another NPC's own blocks)
  that keeps it true.
- Rule 17's trigger reuses rule 16's exact pattern (belief acquisition
  at the witness/retell/corroborate call sites, kinship lookup identical
  to the tell-decision gate's), with a real (not instrumentation-only)
  toggle per the lane-19 precedent — because T4a.2's Run B is designed
  to *be* Run A with rule 17 toggled off, not a hand-authored second
  fixture.

**Needs adjudication** (owner-visible, §8 in the doc):

- **O3 — the new `schedule_rewrite` event type** needs a schema/ADR
  amendment, same status as the Tier-3 doc's escalation-event finding
  (F2 there). This doc proposes the full field set (`npc_id`,
  `location_id`, `start_tick`/`end_tick`, `cause`, `trigger_event_key`,
  `rule`); the owner amends `docs/frame-log-schema.md` §3.
- **O4 — the `framelog.py` edit** is small (drop one filter in
  `serialize_state`, add one `elif` branch to `state_at`) but is the one
  place this design reaches outside `driver.py`/`schedule.py`/
  `events.py`/`rules.py`. Flagging up front so the implementing lane's
  packet lists it explicitly, rather than it surfacing as a boundary
  finding the way lane 24's `framelog.py` branch did.
- **O1 — the `mourning_triggers` claim-slot convention.** `npc_death`
  claims don't currently name the deceased in their own slots (only
  `perpetrator`/`cause`/`location` — the deceased is only reachable via
  the claim's `canonical_event_key`). Proposed fix is the same
  caller-supplies-context idiom as every other Tier-3 mapping, but it's
  new fixture-authoring surface someone has to actually apply when
  building a mourning-eligible death claim.
- **O2/O5 — mourning duration/location tunables.** Placeholders
  (`MOURNING_DURATION_TICKS`, a construction-time destination); the
  ordering requirement is load-bearing, the numbers aren't. Whether the
  north-star fixture eventually needs per-household mourning
  destinations is left open, not needed for T4a.1's single-household
  rung.

**Surprises** (§7/§9 in the doc, the three worth flagging out loud):

1. The schedule-reconstruction gap (above) was already there, just
   never mattered before. This tier is the first one that makes it
   matter, and the recommended design (overlay) happens to fix it as a
   side effect rather than compound it.
2. The roll-identity guarantee really does fall out for free — I went
   in expecting to have to design something (a discriminator, a
   reordering rule, something), and the actual work was proving the
   existing mechanism already has the property and writing down the
   precise precondition that makes it true, so a future refactor
   doesn't accidentally break it without anyone noticing why T4a.2
   started failing.
3. `npc_death` claims not naming the deceased is a small but real gap —
   nothing before this tier ever needed to know "who died" from a
   claim's own content rather than from the event underneath it.

Lane breakdown proposed: L-G (core mechanism + T4a.1 rung, one lane —
its pieces are too coupled to split usefully) then L-H (T4a.2
counterfactual, pure scenario-test once L-G lands, no new production
code). Full detail, dependencies, and file lists in §6 of the doc.
