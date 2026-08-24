# Lane 52 overseer review — M6 role inspector

**Delivered:** `133d28f` (worker-committed; no delivery report filed on
disk — reviewed directly against the commit and the packet, per the
recurring protocol gap already noted for lanes 15/34/46).

**Reviewer:** the coordinator (reassigned this session, `8679f60`,
after the Kimi-lineage coordinator ran out of usage overnight).

## Battery, re-run independently

- `uv run pytest -q`: 249 passed (untouched — zero Python files in the
  commit, confirmed via `git show --stat`).
- `uv run ruff check .`: clean.
- `npm test` (dashboard): **587/587** (83 test files; was 559/80
  before this lane — +28 new tests across `roles.test.ts`,
  `roles.realRun.test.ts`, `reconstruct.test.ts`, `runReader.test.ts`,
  `socialDiff.test.ts`, `RolesScreen.test.ts`, `router/index.test.ts`).
- `npm run build`: clean (`vue-tsc -b && vite build`, 260 modules).
- `npm run check-range --both`: 206 Partial Content on both dev and
  preview.

## Claims verified against the repo, not trusted from the commit message

- **Role-event replay semantics match `chronicle/framelog.py:725-741`
  exactly** — checked field-for-field in `dashboard/src/log/
  reconstruct.ts`'s `applyRoleInstalled`/`applyNpcDiedToRoles`/
  `applyRoleAppointed`: `role_installed` upserts by `role_id`;
  `npc_died` vacates every role whose *current* `holder_id` matches
  the dying NPC, with `vacated_at` read from the event's own `gamets`
  (not the envelope tick) — the exact `framelog.py:735` detail, with a
  documented tick fallback for reader tolerance; `status_changed`
  with `status_kind === "role_appointed"` reads `detail` as the role
  id and `npc_id` as the new holder. This is a careful, accurate port,
  not a paraphrase.
- **The keyframe-windowing fix is real and independently justified.**
  `serialize_state` never writes a `roles` keyframe key (confirmed:
  no `roles` hit anywhere in `chronicle/framelog.py`'s keyframe
  serialization), so a keyframe-windowed replay would silently miss
  any role event before the nearest keyframe — the same class of bug
  the lane-41 finding fixed for `schedule_rewrite`. `RunReader.
  roleEventsUpTo` mirrors `scheduleOverlaysUpTo`'s full-byte-0-scan
  shape. The commit message claims proof-by-reversion (3 of 9
  `runReader.test.ts` tests fail without the fix) — plausible and
  consistent with the lane-41 precedent's own verification method;
  not independently re-run here (would require reverting and
  re-running vitest), but the claim is specific and checks out against
  the code's actual shape.
- **The vacancy-history design point is genuinely subtle and correctly
  reasoned.** `derived/roles.ts`'s header correctly identifies that
  `SocialState.roles` (a replace-mutation roster mirroring `chronicle/
  roles.py`'s `Role` dataclass) cannot recover past vacancy spans once
  a later succession has overwritten `vacated_at` back to `null` — so
  the module does its own single chronological fold over raw events
  rather than reusing the roster map. This is the correct call, not an
  invented complication.
- **Duty-lapse correlation is disclosed as a design choice, not
  discovered as a bug.** A lapse renders for the rest of the run even
  after a later succession (`chronicle/roles.py` has no lapse-clearing
  rule at all) — reasonable given ui-spec §3.10's "duties with lapse
  state" wording, and honestly flagged as the module's own choice
  rather than a spec mandate.

## File boundaries

All 18 changed files are under `dashboard/src/` — no Python, no
frozen docs, no `runs/` data. Two files outside the packet's explicit
Edit list (`components/diff/DiffRow.vue`, `components/diff/
DiffFilterBar.vue`): both are one-key additive edits (`TYPE_LABEL` /
`TYPE_OPTIONS`, both exhaustive `Record<DiffRowType, ...>` types) made
mechanically necessary by `socialDiff.ts`'s new `"role"` `DiffRowType`
— `vue-tsc` would fail otherwise. Both are self-flagged in-file with a
comment explaining exactly this. Judgment call **accepted**: the same
class of boundary call already accepted for lanes 22/38/51 (a packet
naming the primary file for an additive change necessarily implies
its exhaustive-type consumers may need the same one-line addition).
`RunReader.ts` similarly wasn't in the packet's explicit Edit list but
is the correct, precedented location for the full-scan companion to
`reconstruct.ts`'s replay (the `scheduleOverlaysUpTo` shape) —
accepted for the same reason lane-41's fix landed there.

## Ruling

**Accepted.** Battery green across both languages, claims verified
against the actual diff (not the commit message), file-boundary
judgment calls are minimal, self-disclosed, and well precedented.

**M6 complete.** Lane 53 (M7 stranger-walkthrough release gate) is now
startable — it depends on lanes 49 and 52, both landed.
