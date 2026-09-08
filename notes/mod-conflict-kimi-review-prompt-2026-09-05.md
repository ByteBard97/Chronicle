# Prompt for an independent Kimi review of the mod-conflict mitigation plan (2026-09-05)

Hand the text below the line to a fresh Kimi agent session opened in the
Chronicle repo root (`/home/geoff/projects/Chronicle`). Written 2026-09-05.

---

You are reviewing a consolidated design document in the Chronicle repo
(the working directory you were started in). Chronicle is a headless
social-simulation engine for Skyrim SE/AE with a C++ SKSE plugin
(`adapters/skyrim/ChronicleBridge/`) that writes into live game state.
Start by reading `AGENTS.md` and `GOALS.md` for project conventions and
current phase context — note especially GOALS.md's standing doctrine
about not building on infrastructure that hasn't been proven live, and
the gate on ADR-0011 work.

## The task

Critique this document:

- `docs/design/mod-conflict-mitigation-plan.md`

It consolidates ten external research reports into a mitigation plan for
mod conflicts across ChronicleBridge's four game-side write paths (AI
package overrides, a BarterMenu vtable price hook, relationship-rank
writes, persistent evidence-object spawning), and makes a dependency
recommendation (hard-depend on SkyPatcher, stay native on the vendor
price hook, no detect-and-fallback).

The source material it synthesizes, so you can check fidelity:

- `docs/research/mod-conflict-external-reviews-2026-09/` — the ten raw
  reports (Gemini, Kimi, Claude web-research agents; 4 prompts each).
  Read that folder's `README.md` first; it indexes what each report
  contributes and its sourcing quality.
- `notes/mod-conflict-research-prompts-2026-09-05.md` — the original
  prompts the reports answer.

## What a good critique means here

1. **Verify claims against the repo, not the document.** The plan claims
   every external claim was cross-checked against Chronicle's source.
   Spot-check the load-bearing ones yourself. Useful entry points:
   - `adapters/skyrim/ChronicleBridge/src/VendorPriceHook.cpp` (the hook
     the plan describes; note its own UNVERIFIED comment ~line 141)
   - `adapters/skyrim/ChronicleBridge/src/EvidencePoller.cpp` and
     `AvoidancePoller.cpp`, `HydrationPoller.cpp`
   - `adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp` vs.
     `tools/chronicle-patcher/src/IdentityMap.cs` — compare the two
     tables carefully, including the .cs file's header comment
   - `chronicle/diegetic_evidence.py` and the evidence endpoint state
     machine in `adapters/skyrim/listener/listener.py` (search for
     `_EvidenceEntryState`) — the plan's "Open questions" section asks
     whether evidence generation is bounded; this is answerable from
     these files today
   - `tools/chronicle-patcher/` — check whether the Mutagen pipeline
     authors any quests (QUST records) today, since the plan recommends
     an `OnStoryRelationshipChange` listener, which is a Story Manager
     quest event
2. **Check the dependency recommendation's premises.** The SkyPatcher
   hard-dependency call rests on claims about SkyPatcher's ecosystem
   adoption, bus factor, and its exact `.ini` directive syntax. Which of
   those are verified against primary sources vs. research-agent
   assertion? Is the evidentiary bar applied consistently between the
   SkyPatcher-adopt and DPF-reject sides of the split?
3. **Prior critique already raised — verify and extend, don't echo.**
   An advisor pass already filed these six points; the document you are
   reading may or may not address them. For each: is it valid, is it
   addressed in the current text, and if addressed, is the fix actually
   consistent (check the action-items list against the section text)?
   a. Migrating the avoidance patcher (action item 6) may violate
      GOALS.md's freeze doctrine (avoidance's game-side half has never
      been load-ordered in a live game) — the plan takes no position.
   b. The IdentityMap.cpp/IdentityMap.cs deliberate disagreement on
      plugin attribution for 5 of the 19 NPCs is a landmine for
      SkyPatcher `.ini` generation and is not mentioned.
   c. `OnStoryRelationshipChange` quietly imports quest authoring +
      Papyrus into a C++-only architecture; not flagged as a new
      mechanism class.
   d. The "is evidence generation bounded?" open question is answerable
      now from `chronicle/diegetic_evidence.py` + the listener.
   e. Action item 7 (does vendor-markup earn its keep vs. Trade and
      Barter) should gate action item 1, not follow it.
   f. GOALS.md doesn't reference this plan, and none of it is committed.
4. **What did everyone miss?** The value of a fresh pass is findings
   none of the ten reports, the synthesis, or the advisor made. Check
   failure modes across the four write paths that the prompt framing
   itself may have excluded (e.g. interactions between the paths,
   save/load interaction with the sync handshake, listener-restart
   behavior, the 19-NPC fixed scope itself as a risk).

## Constraints

- Review only. Do not edit the plan, the source reports, or any code.
- Distinguish clearly: verified fact (cite file:line), claim you
  confirmed from the source reports (cite which report), and judgment
  calls.
- Where you disagree with the plan or the advisor points, say so
  directly with evidence.

## Deliverable

Write your critique to
`docs/research/mod-conflict-external-reviews-2026-09/kimi-review-2026-09-05.md`
with: a verdict paragraph (is this plan sound enough to act on, and
which action items are safe to start now vs. which need the flagged
verification first), a numbered findings list ordered by severity, and
for each finding the specific edit the plan needs. Keep it under ~300
lines.
