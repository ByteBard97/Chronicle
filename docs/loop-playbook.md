# Loop playbook

Read this at the start of every `/loop` iteration on Chronicle, alongside
`AGENTS.md` (governance/conventions, read first) and
`docs/design/next-phases-2026-08.md` (the current work queue — the
source of truth for "what's next," update it as things land or new gaps
surface).

## What one loop iteration does

1. **Check `docs/design/next-phases-2026-08.md`** for the next unblocked
   item. If the top candidate needs owner sign-off (spends the ladder's
   last rule-budget slot, touches a frozen document, needs the Windows
   build machine / a live game) — don't do it. Move to the next
   candidate and say why the blocked one was skipped, once, in your
   summary; don't ask the question again next iteration if nothing has
   changed.
2. **If the next item has no design-prep doc yet**, write one first
   (`docs/design/*.md`, modeled on the existing ones — name the real
   dependency it doesn't build, scope the smallest real slice, cite
   file:line for every claim). Commit it before writing code, same as
   every lane this session.
3. **Implement via a dispatched agent** (`Agent` tool,
   `subagent_type: general-purpose`), not inline edits — write a
   self-contained prompt with full context (the agent starts with none):
   what to read first, the exact scope boundary, what NOT to touch, what
   tests to add, what command to run to verify. This session's prompts
   in the transcript around commits `c6d047d`/`c5aa674`/`eea96c1` are
   the template for how much context a prompt needs.
4. **Review every agent's diff yourself before trusting its report.**
   Read the actual changed files (`git diff`), don't just read the
   agent's summary — this session caught real errors this way (a wrong
   latch key, an invented trigger mechanism, a scope collision with a
   landed test) that the agent's own report didn't flag. If something's
   off, fix it or dispatch a follow-up agent; don't commit until it's
   right.
5. **Run the full battery** before committing: `uv run pytest chronicle/tests/ scenarios/ -q` at minimum; `make check` if touching the dashboard.
6. **Commit locally, path-scoped, never `-a`/`-A`** (AGENTS.md). Write a
   commit message that states what changed and *why*, not just what
   files moved.
7. **Do not `git push` on your own.** AGENTS.md's governance model and
   this repo's global rules both require explicit owner permission per
   push, even mid-loop. Accumulate local commits; ask (or wait to be
   asked) before pushing, unless the owner has separately told this loop
   specifically that it may push freely — if that permission was given,
   note it here so future iterations know, and note when/if it's
   revoked.
8. **Update `docs/design/next-phases-2026-08.md`** with what landed and
   what it surfaced — this session's own history is the model: landing
   rules 12/13 surfaced that v0.3 was mostly already built; landing
   `sync.py` surfaced that fork-on-disk support doesn't exist. Expect
   every lane to reshape the plan; write that down rather than letting
   the doc go stale.

## Standing constraints (don't relitigate these each iteration)

- Frozen, owner-review-only: `docs/ui-spec.md`, `docs/scenario-ladder.md`,
  `docs/ui-doctrines.md`. Findings route to the owner, never edited in a
  lane.
- The scenario ladder's rule-budget is at its ceiling minus one slot.
  Don't spend it without being told to.
- Other sessions work this repo concurrently (a Kimi coordinator
  lineage, the owner's own game-modding session). If you see an
  unexpected diff in a file you didn't touch (this session hit this with
  `docs/work-packets/reviews/README.md` more than once) — leave it
  alone, it's not yours to revert or resolve.
- `adapters/skyrim/`'s native (C++) half and anything needing a live
  game session or the Windows build machine: name it, design around it,
  don't attempt it from here.
- `runs/` is gitignored; never commit run data. Determinism is
  load-bearing — same seed must produce byte-identical logs modulo
  `wall_ts`.

## When there's nothing left to do safely without the owner

Say so plainly and stop cleanly (or, in `/loop` dynamic mode, schedule a
longer-interval wake-up rather than a short poll) — don't invent busywork
or start touching frozen documents to look productive. Name what you'd
do next and what decision it's waiting on.
