# Next-phase discussion prep — 2026-09-01 (Kimi coordinator synthesis)

Purpose: input for the owner/Kimi/advisor "what next" conversation after the
sync-handshake work lands. Sources: GOALS.md, vision-v2.2, scenario-ladder,
lane board, next-phases-2026-08, HANDOFF-2026-08-29-2003, open-questions.md,
ADR-0011 + conversation-tier design notes, research reports 34–48, and the
sync-handshake spec v2 + review.

## Where the project actually is (2026-09-01)

**Done:** scenario ladder T0–T6 all green (20 rules, north-star composition);
dashboard v1 M0–M7 with release gate PASS; 7 ChronicleBridge slices live-verified
at state level (14/16); fork-on-disk + `sync-check --apply`; sync-handshake C++
core + listener endpoints + wire-contract test (commits acc71dc..98aa019);
launch-prep repo work (README/CONTRIBUTING/CI, `make check` green).

**In flight:** sync-handshake *wiring* — SyncHandshakeCore is not yet hooked into
`plugin.cpp` (no SerializationInterface co-save, no messaging hooks). Landed
outside the lane/packet system — board should be updated retroactively.

**Blocked/parked:** `game action=load` no-op (4 experiments failed; next
experiment is the MO2 launch path; needs owner). Player-*visible* confirmation
of bridge writes ("M5-live") — needs an owner game session. Live FORK
verification is gated on the load bug. Rule-11 hysteresis needs a rule-ceiling
ruling. QoL mod installs need owner Nexus downloads.

**Newly design-ready:** the conversation tier. The 48-hour research burst
(34–48) settled the model question (GLM-4.7-Flash primary / Qwen3-30B-A3B-2507
fallback, gated on one 5-minute `cache_n` check when the M5 Pro arrives), TTS
(mlx-audio native, single-process), lip sync (Mfg Fix NG procedural default,
`.lip` Windows fallback), validated "engine decides, LLM renders" against 20
years of prior art, and confirmed no shipped system does what Chronicle does.

## The sequencing argument

GOALS.md's own doctrine — "no LLM before symbolic tiers are green" — is now
satisfied: the ladder is complete. The conversation tier is the first LLM work
the project rules *allow*, and the research burst just made it the best-understood
unbuilt thing in the project. Meanwhile three loose threads are cheap to close
and two of them are load-bearing for everything player-facing:

1. **The sync handshake is prerequisite infrastructure, not a side quest.**
   ADR-0011 stores persona per `save_uuid`; conversation utterances are claims
   that must survive save/reload correctly. Any real gameplay feature built
   before the handshake is wired will accumulate exactly the timeline-corruption
   risk the handshake exists to prevent. It's also ~90% done.
2. **Player-visible verification (M5-live) is the honesty gate on the whole
   bridge** — state-level verification proved the writes land; nobody has
   watched an NPC visibly walk apart. One owner game session closes it.
3. **The load bug** gates both the last 2 live tests and live FORK
   verification. One owner experiment (MO2 launch path) may close it.

The conversation tier's hardware-gated parts (on-device latency validation)
can't run until the M5 Pro arrives anyway — but its **deterministic core needs
no hardware at all** and is the bulk of the work.

## Recommended shape: three tracks

### Track 1 — Close out (days; owner + Windows build machine)

- Wire SyncHandshakeCore into `plugin.cpp` per spec v2 (co-save + messaging).
  Coordinator note: verify delivered work lands *in the repo* this time — the
  core landed via direct commits outside the packet system; return to lanes for
  the wiring.
- Owner: MO2-launch experiment for the `load` bug → if it clears, last 2 live
  tests + live FORK test → call M3 done (owner judgment).
- Owner: M5-live player-visibility session.
- Owner: launch-prep external steps (GitHub issues, Discord link, push, post).
  Report 36 says: SKSE/Mutagen Discords, **not** r/skyrimmods.

### Track 2 — Conversation tier, deterministic core (the main next phase; no hardware needed)

Owner decisions first (research has de-risked all six open questions):

1. **ADR-0011: accept** with the design-notes amendment (engine-authored
   parameterized-intent menus, one line per tap).
2. **Confirm-vs-autoplay** → report 43's empirical answer: 24% of raw outputs
   fail intent-correspondence → ship an automated CICERO-style filter
   *regardless*; confirm-first default, auto-speak as a setting (doubles as the
   natural experiment).
3. **Free-form path** → report 39's staged plan: Phase 0 menu-only; Phase 1
   flagged + player-confirmed; remove confirmation only if measured correction
   rate <2–3%. Decision made, build Phase 0.
4. **Menu ranking** → small deterministic design note; 43 recommends
   CiF-volition-style scoring.
5. **Annotation set** → freeze v1 (emphasis / pause / laugh / tone enum) before
   the first TTS adapter.
6. **Audio delivery** → spike: HTTP ring buffer + Mfg Fix NG procedural mouth
   (report 44); testable with pre-recorded audio, no TTS needed.

Then lanes, in dependency order:

- **Engine lane:** utterance origin kind in `claims.py` (ADR-0011 consequence;
  borrow Talk-of-the-Town's origination taxonomy per report 43) + the
  menu-construction query (pure state function, unit-testable) + the scenario
  test ADR-0011 already names ("player boast mutates as it travels").
- **Service lane:** voice-card compiler (deterministic), canonical segmented
  prompt renderer (cache-prefix discipline from notes §4), intent-correspondence
  filter, OpenAI-compatible endpoint abstraction (hosted model usable *today*),
  recorded-fixture replay eval harness.
- **Bridge lane:** the audio-delivery spike (above) — the last genuinely unknown
  technical risk in the tier.

### Track 3 — Consciously deferred (say so out loud)

- Rule-11 hysteresis: hardest open symbolic problem; needs a rule-ceiling
  ruling. Do it when the owner wants a symbolic palate cleanser, not now.
- v0.4 economy, GM/director layer: stay deferred per GOALS.md.
- On-device model validation (`cache_n` check, GLM vs Qwen bake-off): when the
  M5 Pro arrives, not before.

## Questions to put to the advisor

1. Do you agree the sync handshake is correctly treated as *prerequisite* to any
   player-facing conversation work, or is there a safe interim where dialogue
   lands without branch-correctness?
2. Is accepting ADR-0011 now (with the menu amendment) premature given the
   confirm-vs-autoplay question technically sits inside it — or does the
   filter-plus-confirm-first answer make that moot?
3. Track 2's engine lane adds the first player-originated claim kind — does
   that interact with anything in the frozen docs (ui-spec, scenario-ladder)
   that needs owner review before a lane starts?
4. Is the audio-delivery spike correctly placed *early* (risk retirement) rather
   than in pipeline order (it would naturally come last)?
