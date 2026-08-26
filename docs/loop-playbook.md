# Loop playbook

Read this at the start of every `/loop` iteration on Chronicle, alongside
`AGENTS.md` (governance/conventions, read first) and
`docs/design/next-phases-2026-08.md` (the current work queue — the
source of truth for "what's next," update it as things land or new gaps
surface).

## What one loop iteration does

1. **Check `docs/design/next-phases-2026-08.md`** for the next unblocked
   item. Distinguish two different kinds of "blocked" (the owner has
   said, repeatedly, that they don't have opinions on the first kind and
   the loop must stop routing it back to them):
   - **A domain/tuning question** — a constant, a curve shape, which of
     two defensible readings of a schema, a tie-break between two AI
     reviewers who disagree: **resolve it yourself.** Consult Kimi and
     advisor, verify the discriminating fact in the code if there is
     one (prefer whichever answer is grounded in something you can check
     — a type constraint, an existing convention — over the one that's
     merely better-argued in prose), make an executive call, write the
     rationale down in the design doc, and proceed. Do not present two
     options and wait; a design doc that ends in "the owner should
     decide X vs Y" for a question like this is unfinished, not done.
   - **A genuinely irreversible-or-preference question** — pushing to
     the remote, deleting data, a product-direction call with no
     technical answer (do we want feature A or B at all): this is the
     only kind that should actually stop the loop and wait. This
     category is narrow and shrinking, not a default — checked again
     and re-narrowed 2026-08-26 after repeated, escalating owner
     feedback ("stop asking stupid questions... do not halt like this
     again"). **Researching whether something is feasible, what prior
     art says, or writing a design doc is never in this category** —
     only actually spending a scarce, ceiling-limited resource (the
     ladder's rule budget) on new implementation is, and even that only
     needs a heads-up in the commit message, not a pause for
     permission. When in doubt, the default is: research it (Kimi,
     advisor, or a fresh research agent — Kimi being temporarily out of
     quota is not a reason to fall back to asking the owner instead),
     decide, and proceed.
   A frozen document (`docs/ui-spec.md`, `docs/scenario-ladder.md`,
   `docs/ui-doctrines.md`) being touched is not automatically the second
   kind — "frozen" means "don't edit casually on a whim," not "never
   edit." A design doc that has been through real review and rules
   cleanly on its open questions may amend a frozen doc's stale count or
   add a properly-scoped new row; report the amendment afterward rather
   than asking permission first. SSH access to the owner's Windows
   build machine exists (`.claude/windows-build-machine.md`, gitignored
   — read it) and retires the "needs the Windows build machine" excuse
   for ChronicleBridge C++ work entirely — compiling and iterating
   against real CommonLibSSE-NG headers is reachable from this session.
   Only *actually running the game* (a live save, real player input)
   remains a genuine, first-kind-of-blocked stop.
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

- Frozen, owner-review-only in the sense of "don't edit casually":
  `docs/ui-spec.md`, `docs/scenario-ladder.md`, `docs/ui-doctrines.md`.
  A design doc that went through real review and rules cleanly on its
  own questions may amend one (report afterward); don't rewrite one on
  a whim or without that review trail.
- The scenario ladder is at its full ~20-rule ceiling as of rule 20
  (2026-08-26) — zero slots free. A new mechanism needs a fresh
  consolidation ruling or an explicit ceiling raise before landing, not
  before *researching* — see the narrowed rule above.
- Other sessions work this repo concurrently (a Kimi coordinator
  lineage, the owner's own game-modding session). If you see an
  unexpected diff in a file you didn't touch (this session hit this with
  `docs/work-packets/reviews/README.md` more than once) — leave it
  alone, it's not yours to revert or resolve.
- `adapters/skyrim/ChronicleBridge/`'s native (C++) half is now directly
  reachable: SSH build access to the owner's Windows machine exists
  (`.claude/windows-build-machine.md`) and this session verified real
  compile-iteration works. Only actually running the game against a
  live save is out of reach from here — compiling, iterating on real
  compiler errors, and landing C++ changes is not.
- `runs/` is gitignored; never commit run data. Determinism is
  load-bearing — same seed must produce byte-identical logs modulo
  `wall_ts`.

## When there's nothing left to do safely without the owner

Say so plainly and stop cleanly (or, in `/loop` dynamic mode, schedule a
longer-interval wake-up rather than a short poll) — don't invent busywork
or start touching frozen documents to look productive. Name what you'd
do next and what decision it's waiting on.
