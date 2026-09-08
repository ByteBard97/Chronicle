# Radiant Story Integration Surface: Primary-Source Verification (2026-09-06)

Chronicle's vision (`docs/vision-v3.0.md`) and master synthesis stake the
headline mechanic on a specific claimed integration surface: `SendStoryEvent`
+ `ForceRefTo`/`ForceRefIfEmpty` + `OnStory*` events, all vanilla Papyrus, no
SKSE dependency. That claim traces back to a three-agent (Gemini/Claude/Kimi)
synthesis built from documentation/community-writeup summaries, not from
directly reading Creation Kit wiki pages or real mod source — exactly the
claim-shape that broke under verification four times already this session
(HAMLET, Talk of the Town's stripped repo, SkyPatcher's nonexistent
`packageListAdd`, Ensemble's false "maintained" status). This verifies the
claim directly against the Creation Kit wiki and Papyrus reference sites,
not secondhand summaries.

## 1. Function-by-function verification

**`SendStoryEvent`** — **Confirmed real**, a member of the base-game
`Keyword` script (`Keyword.psc`, vanilla, not an SKSE extension class):
`SendStoryEvent(Location akLoc, ObjectReference akRef1, ObjectReference
akRef2, Int aiValue1, Int aiValue2)` — "sends this keyword as a story event
to the story manager." A second, undocumented-in-Chronicle's-prior-research
variant also exists: **`SendStoryEventAndWait`** — same signature, but
"waits for it to be processed, returning true if a quest was started." This
is a real, useful primitive Chronicle should adopt: it gives synchronous
confirmation of whether a casting attempt actually landed, rather than
firing blind. *Sources: CK Wiki Keyword Script page; TES Alliance forum
thread "SendStoryEvent (Keyword)"; multiple gamesas.com forum threads
independently describing identical usage.*

**`ForceRefTo`** — **Confirmed real**, `ReferenceAlias` script:
`ForceRefTo(ObjectReference akNewRef)` — "Forces this alias to use the
specified reference." Documented caveats not in Chronicle's prior research:
- Triggers **package re-evaluation for every actor in any currently running
  scene in the quest** — "calling this multiple times in a row can result
  in actors in running scenes losing their scene package permanently."
  **This is a real, new risk**: Chronicle's design needs a debounce/guard so
  a belief-graph update doesn't call `ForceRefTo` repeatedly on the same
  alias in quick succession.
- **Cannot clear an alias to None** — must use `ReferenceAlias.Clear()`
  instead.
- **Asynchronous, not immediate**: "does not yield and wait for the alias's
  reference to reflect that of the new forced value... the reference will
  be forced rapidly, not immediately." **Real race-condition risk**: code
  that reads the alias immediately after calling `ForceRefTo` may still see
  the old value.
- Repeated calls to the same alias execute in call order, approximately.
- "Does appear to bypass many if not most CK fill conditions" but "can
  still fail under certain conditions" — the wiki itself leaves this
  unspecified. Worth a small empirical spike before committing engineering
  budget: does it fail if the target is already force-filled into a
  different alias, already dead, or in a different worldspace?

**`ForceRefIfEmpty`** — confirmed real, same script, conditional variant
(only fills if the alias is currently empty).

**`OnStory*` events** — confirmed real as a named event family on the
`Quest` script. `OnStoryActivateActor` has its own dedicated Papyrus-Index
page (papyrus.bellcube.dev) with full signature detail. `OnStoryKillActor`
is independently confirmed via the CK Wiki's "SM Event Node" page (the
Story Manager node type that fires when "an Actor is murdered"). Naming
convention is `OnStory<EventName>`, PascalCase.

## 2. Behavioral verification (the caveats an advisor flagged as plausible)

**Event consumption is real but configurable, not an absolute rule.**
Correcting the prior synthesis's flatter framing: Story Manager event
consumption is governed by a **per-node "Shares Event" setting**. If a node
is *not* marked "Shares Event," the event is consumed and the Story Manager
stops once that node finishes processing it. If it *is* marked shared,
multiple quests can process the same event. **Design implication**:
Chronicle should explicitly author its own Story Manager nodes as
non-shared, one node per intended story-type, rather than relying on this
as an automatic engine guarantee — it's an authoring decision Chronicle
controls, not a hard constraint to route around.

**Alias-fill failure independently confirmed to kill the quest silently.**
"Once a quest is selected... it will attempt to start that quest and fill
all its quest aliases. If the quest aliases cannot be filled, the quest
fails to start and the Story Manager attempts to start another quest." This
directly corroborates the worked design tour's caution (ship every alias
optional, plus a stage-0 validation script) — that mitigation is necessary,
not overcautious.

**The "must be loaded" constraint applies to a different fill mechanism
than the one Chronicle plans to use — this is good news.** The
condition-based **"Find Matching Reference"** fill type's "Closest" sort
option explicitly requires "In Loaded Area" ("only works in the loaded
areas"). But Chronicle's design (per vision-v3.0 and the worked design
tour) explicitly avoids condition-based fill in favor of **direct
`ForceRefTo`/`ForceRefIfEmpty` calls with an already-resolved
`ObjectReference`** to a real, named NPC. Named/unique Skyrim actors are
persistent references, resolvable and manipulable by script (e.g.
`Actor.MoveTo()`) whether or not they're currently loaded — a well-
established modding pattern, not a Chronicle-specific workaround. The
worked design tour's own mitigation ("Chronicle casts named NPCs by
explicit reference, which sidesteps this") is correct and holds up.

**SKSE dependency: confirmed vanilla.** `SendStoryEvent` lives in the base
`Keyword.psc`, not an SKSE-extended script class (SKSE does add its *own*,
separate member functions to `Keyword` for unrelated purposes, which is
likely the source of any confusion, but the story-event functions
themselves are base Papyrus).

## 3. Honest gap in this verification

I did not read a real, complete mod's `.psc` source directly calling
`SendStoryEvent` end-to-end — both `ck.uesp.net` and `nexusmods.com` return
HTTP 403 to automated fetches, and the specific step-by-step Nexus guide
("How to Start a Quest Using Script Event in the Story Manager") could not
be read directly for the same reason. What this verification instead relies
on: the Papyrus Index's direct function-signature pages (a genuine primary
source — auto-generated from the actual compiled script source, not a
paraphrase) plus multiple independent community forum threads (TES
Alliance, gamesas.com) describing identical behavior consistently and in
technical detail. This is meaningfully stronger evidence than the prior
three-agent synthesis (which cited no primary source directly), but it
falls short of reading one real mod's working implementation end-to-end.
**Recommended as a five-minute follow-up, not a blocker**: find and read one
real shipped mod's actual script calling `SendStoryEvent` before writing
Chronicle's first line of Papyrus against this surface.

## 4. Verdict

**The claimed integration surface holds up.** This is the rare case in this
session's verification track record where an AI-research-synthesized claim
survives direct primary-source checking rather than joining the pattern of
HAMLET/Talk-of-the-Town/SkyPatcher/Ensemble failures — `SendStoryEvent`,
`ForceRefTo`, `ForceRefIfEmpty`, and the `OnStory*` event family are all
real, vanilla, non-SKSE-dependent, exactly as claimed.

It does **not** hold up "exactly as described" with zero adjustment,
though — three real caveats surfaced here were absent from the prior
synthesis and need to be designed around, not just noted:
1. **A debounce/guard on `ForceRefTo` per alias** — repeated calls in quick
   succession risk permanently breaking a running scene's package
   assignment.
2. **An async-read guard** — never assume an alias's reference is updated
   immediately after calling `ForceRefTo`; the change is "rapid, not
   immediate."
3. **Explicit non-shared Story Manager node authoring** per story-type,
   since event consumption is a configurable setting Chronicle controls,
   not an automatic engine guarantee.

None of these invalidate "Radiant Story integration first" as a build-order
decision — they're implementation-plan-level details, not architecture-
level red flags. The headline mechanic's technical foundation is sound.
