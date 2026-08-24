# Lane 50 delivery report — T2.4 motivated-mutation hook

**Delivered:** `f181e88` — the `allegiance_candidates` hook in
`chronicle/driver.py`'s `_decide_mutation`, and
`scenarios/test_tier2_motivated_mutation.py`. Per the ruled design
(`docs/design/north-star-fixture.md` Decision N4).

## Acceptance, per criterion

- **`uv run pytest -q` green (240 + new tests), ruff clean.** ✓ — 246
  passed, 0 failed, 0 xfailed (242 prior + 4). `uv run ruff check .`:
  clean.
- **Substitution direction matches allegiance, asserted exactly;
  unmapped tellers unchanged.** ✓ — four tests:
  1. A Stormcloak-aligned teller's mutation substitutes to exactly
     `"an Imperial plot"` (the mapped value), not merely a member of
     some candidate set.
  2. The same fixture re-run at three different tick offsets always
     produces the identical value — proof there's genuinely no roll
     deciding it, not just a lucky single observation.
  3. An unaligned teller (no faction edge at all) keeps today's
     uniform-random behavior, substituting from `mutation_candidates`
     and never producing the allegiance value.
  4. The full regression case: the *same* faction-aligned teller, with
     `allegiance_candidates=None`, falls back to the uniform-random
     pool — proving the hook is additive, not a behavior change for
     anyone not opted in.
- **No new rules, no new RNG purposes.** ✓ — `git diff chronicle/rules.py
  chronicle/rng.py` for this lane is empty. The hook lives entirely
  inside rule 7's existing `_decide_mutation`, as a caller-supplied
  policy input, exactly as the design doc specified.

## What was built

`Driver.__init__` gains `allegiance_candidates: Mapping[tuple[str, str,
str], str] | None = None` (claim_kind, slot, faction `basis_id`) → the
deterministic substitution value. Inside `_decide_mutation`, right
after the slot is chosen (and its roll key computed, now shared with
the fallback path via a local `slot_key` rather than recomputed
twice), the driver looks up the teller's `"faction"` relationship via
`self.social.relationships_from(teller_id)` (a read-only bulk scan, no
new `social.py` accessor needed — `relationships_from` already
existed) and checks `allegiance_candidates` for that faction's
`basis_id`. A hit (that isn't a no-op) returns immediately with a
`_MutationDecision` built from a deterministically-derived
`mutation_id` (hashing the slot roll's key plus the allegiance value —
still reproducible on replay, never a random UUID) and **skips the
`mutation.value` roll entirely**. A miss falls through to the existing
uniform-random path, completely unchanged.

## Findings

1. **`mutation_applied`'s `roll_key` field is, and remains, the slot
   roll's key — unconditionally.** The existing code (predating this
   lane) only ever embeds the *slot* roll's key in this field, with a
   comment explaining the *value* roll's key is "derivable" from it
   (same `tick`/`site`/`participants`, different `purpose`) rather than
   stored separately — there is no distinct `value_roll_key` field in
   the record at all. Given that, the packet's schema-gloss phrase
   "`roll_key` ... null on the value side when the substitution was
   deterministic" can't refer to a literal field write (nothing to
   null — there's only one field, and it's the slot's). I've
   implemented it as: `roll_key` stays populated with the slot roll's
   key always (the slot genuinely is randomly chosen either way), and
   the "null value side" is a conceptual fact — no `mutation.value`
   roll exists to derive from it in the deterministic case, which the
   record's absence of any value-purpose evidence already correctly
   implies. Verified in the rung test
   (`mutation["roll_key"]["purpose"] == "mutation.slot"`, always). If
   the coordinator intended a literal new field, that's a schema change
   beyond what "gloss" suggested, and would need its own ruling.
2. **No `social.py` changes needed.** `relationships_from(from_id)`
   already existed (pre-dating this lane) and was exactly the bulk
   accessor the hook needed — the packet's read-first list correctly
   anticipated this ("the bulk-accessor idiom, lane 43's `grudges()`"
   turned out to already have an even more direct precedent already in
   place).
3. **No deviations from the packet's file boundaries.** Only
   `chronicle/driver.py` edited; `chronicle/rules.py`, `chronicle/rng.py`,
   `chronicle/social.py` untouched, per the packet.
