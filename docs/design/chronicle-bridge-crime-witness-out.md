# Design prep — ChronicleBridge, a `crime_witnessed` slice: does it need a new rule?

**Determination: reuses existing rules. No new-rule-budget spend, no owner
sign-off required for the Python-only cut below.** The scenario ladder's
rule registry is at its 20-rule cap (`chronicle/tests/test_rules.py`:
`assert len(names) == 20`), so this question had to be settled before
anything else. It resolves cleanly: the crime-witness cascade this doc
proposes dispatches between two *already-registered* rule-gated
primitives — `Driver.suffer_harm()` (rule 12, `GRUDGE_CREATION`) when the
witness is the crime's own victim, and the plain `Driver.witness()`
primitive (rules 10/11/16/17's shared belief-formation hook) when they are
not. Neither path invents a rule, a store, or a new gate. This is
therefore **not** the same category of decision as
`docs/design/rule11-bidirectional-hysteresis.md` (spending the last rule
slot) — that doc's "design-ready, NOT approved" callout does not apply
here, and this doc is not making that callout. What follows is scoped,
implementable, Python-only, matching the hydration/avoidance/vendor-markup
precedent.

Sources read in full: `docs/research/29-crime-witness-event-extraction.md`,
`docs/research/30-crime-witness-prior-art-spike.md` (the C++-side prior
art — see §4, deliberately unscoped here); `chronicle/driver.py`'s
`suffer_harm()`, `witness()`, `_evaluate_accumulation()`,
`_apply_reputation()`, `inject_event()`; `chronicle/rules.py`'s
`GrudgeCreationRule`/`AccumulationThresholdRule`; `chronicle/claims.py`'s
`witness()`/`retell()`; `docs/design/next-phases-2026-08.md` §0 (rules
12/13's landing, `c6d047d`); `docs/design/rule11-bidirectional-hysteresis.md`
(the house-style precedent for flagging a rule-budget decision, cited above
to explain why this doc does *not* need the same flag);
`adapters/skyrim/ChronicleBridge/src/DeathEventSink.h`/`.cpp`;
`adapters/skyrim/listener/listener.py`; `chronicle/events.py`,
`chronicle/cli.py`, `chronicle/framelog.py`, `docs/frame-log-schema.md` §3;
`adapters/skyrim/listener/models.py` and the generated OpenAPI contract.

## 0. A finding that reframes the whole task: `crime_witnessed` already exists, half-built

Before designing anything, it's worth being explicit about what's already
in the codebase, because it changes the shape of "what's left":

- **`crime_witnessed` is already a tier-0 canonical event kind** on the
  Chronicle side — `chronicle/events.py`'s `CrimeWitnessed` dataclass
  (`witness_id`, `perpetrator_id`, `crime_type`, `location_id: str | None`),
  wired into `chronicle/framelog.py`'s `event_payload()`/`event_from_record()`,
  and registered in `chronicle/cli.py`'s `_EVENT_FIELDS`/`_EVENT_CLASSES`/
  `_ACTOR_FIELD`. `docs/frame-log-schema.md` §3 lists it at tier 0, the same
  tier as `npc_died`. `chronicle inject <run> --event '{"event_type":
  "crime_witnessed", ...}'` already works today.
- **It has zero cascade wiring.** `inject_event()` (`driver.py`) only
  appends the canonical-event record and, for `NPCDied`, runs an *objective*
  cascade (role vacancy) — no belief, no grudge, for any event kind. This
  matches `npc_died`'s own precedent exactly: `docs/design/
  chronicle-bridge-death-extraction.md` never wires deaths into
  `witness()`/mourning either; a scenario author calls `witness()` (and
  registers `mourning_triggers`) separately, by hand, keyed to the claim
  kind. `crime_witnessed` has never had that second half built. This design
  doc's actual Python deliverable is that second half.
- **The ChronicleBridge/listener transport layer does not know
  `crime_witnessed` at all.** `adapters/skyrim/listener/models.py`'s
  generated `EventType` enum has exactly one member, `npc_died`
  (`"Only 'npc_died' exists in this slice"`), and `listener.py`'s
  `_inject_death_event()` hard-codes the death payload's four fields. The
  `/whiterun/events` route itself is generic (`_handle_events()` just
  validates against `GameEvent` and shells out), but the contract behind it
  is death-only. Extending it is a contract/generation change, not a new
  route — see §3.

None of this required new reverse-engineering to discover; it's a direct
read of code already in the tree. It matters for scoping because the
"first cut" here is smaller than "invent an event and a cascade" — it's
"finish wiring an event that already exists, on the Python side only."

## 1. The modeling question, answered concretely

`suffer_harm()`'s own docstring forecloses the naive answer:

> Self-victim only (O3's bypass, same as `violate_obligation`): `holder_id`
> is both the grudge's `holder_id` and `victim_id`... There is no
> third-party-harm path here; an NPC who merely witnesses harm to someone
> else acquires their own belief about it through the ordinary `witness()`
> path, not through this method.

A `crime_witnessed` event names a **witness**, not necessarily a victim.
The player can commit a crime against a third party (assault on NPC B,
witnessed by NPC A) or against no specific person at all (theft from a
shop, trespassing, a bounty-tier crime with only a faction on the other
end). Feeding `witness_id` into `suffer_harm()` unconditionally would be
wrong twice over: it would mint a `Grudge` with `victim_id = witness_id`
(via O3's bypass) even when the witness wasn't harmed, misrepresenting them
as a crime victim in the social-state store; and it would do it via rule
12, whose own docstring says exactly this case is out of scope.

But `witness()` already *is* the modeled primitive for "an NPC witnessed an
event and formed a belief about it," independent of whether they were
harmed — confirmed by reading it in `chronicle/claims.py` (a `Claim` +
high-confidence `BeliefInstance` + `"witnessed"` `Evidence`, no notion of
victimhood anywhere in its signature) and its driver wrapper
(`Driver.witness()`, `driver.py:569`), which runs rules 10
(`WITNESS_CREATES_BELIEF`), 4 (`SHARED_CLAIM_INVARIANT`), 11
(`ACCUMULATION_THRESHOLD`, gated on the holder being the claim's *named
victim slot* — a no-op for a bystander witness), 16
(`REPUTATION_ACCUMULATION`, keyed only by claim kind — this is exactly the
mechanism that should let a bystander's witnessed crime dent the
perpetrator's reputation without any grudge at all), and 17 (mourning,
irrelevant here). This is precisely the "existing-rule-compatible
witness-belief-formation path, distinct from 'I was harmed'" the task
asked to check for. It exists, unmodified, today.

So the honest split is by **role**, not by inventing a new mechanism:

| witness's relationship to the crime | call path | rule(s) exercised |
|---|---|---|
| witness **is** the crime's victim | `witness()` then `suffer_harm()` | 10, 4, 16 (belief); 12 (grudge) |
| witness is a **bystander** (crime against a third party, or victimless/property) | `witness()` only | 10, 4, 16 (belief + perpetrator's reputation hit); no grudge |

Both rows are 100% existing machinery. Rule 12's self-victim invariant
isn't a gap this design has to work around — it's the correct boundary,
and the bystander row is what `witness()`-without-`suffer_harm()` was
already built to express.

## 2. Event schema

`CrimeWitnessed` (`chronicle/events.py`) needs exactly one additive field
to let a producer *express* which row of §1's table applies — it currently
has no victim concept at all:

```python
@dataclass(frozen=True)
class CrimeWitnessed(Event):
    """An NPC observed another NPC (often the player) commit a crime."""

    witness_id: str
    perpetrator_id: str
    crime_type: str
    victim_id: str | None = None    # NEW. None = no specific human victim
                                     # (property/bounty crime) or unknown.
    location_id: str | None = None
```

- **`victim_id: str | None = None`** — optional, additive, same pattern as
  `npc_died`'s own `killer_id`/`location_id` becoming optional fields on an
  already-shipped event kind. `None` means "no specific victim" (a shop
  theft, trespassing, a bounty-only crime) or "not yet resolved" — either
  way it conservatively routes to the bystander row (belief only, no
  grudge), never the reverse. When `victim_id == witness_id`, this event
  *is* the victim's own witness account of their own victimization, and
  routes to the grudge row.
- **`crime_type: str`** (already present) doubles as the `Claim.kind` for
  the belief this event produces — e.g. `"assault"`, `"theft"`,
  `"trespassing"`. This is deliberate reuse: it's the same free-form string
  key `accumulation_thresholds` (rule 11) and `reputation_relevance` (rule
  16) already index by (T3.1's fixture uses `"theft"` exactly this way), so
  a scenario author who wants rule 11 escalation or rule 16 reputation
  wired to crime claims registers those mappings the ordinary way — no new
  registration mechanism, just using the ones that exist.
- **`witness_id` / `perpetrator_id`** (already present) are `npc_id`-style
  Chronicle identities, matching this project's FormID-never-persisted
  discipline throughout — no change needed, they already fit.
- **`location_id: str | None`** (already present) — unchanged.
- Multiple witnesses to one crime become multiple `crime_witnessed` events
  (one per `witness_id`), matching report 29/30's `actorsKnowOfCrime`
  array shape and this schema's existing one-event-per-witness design —
  not a new list-valued field.

`docs/frame-log-schema.md` §3's `crime_witnessed` row and
`chronicle/cli.py`'s `_EVENT_FIELDS["crime_witnessed"]` both need the same
additive `"victim_id": False` entry.

## 3. The driver-side cascade (the actual new code)

A new `Driver.crime_witnessed()` wrapper in `chronicle/driver.py`, in the
same family as `witness()`/`retell()`/`corroborate()` — a thin, trace-
emitting orchestration method, not a new rule:

```python
def crime_witnessed(
    self,
    *,
    claim_id: str,
    belief_id: str,
    evidence_id: str,
    witness_id: str,
    perpetrator_id: str,
    crime_type: str,
    victim_id: str | None,
    location_id: str | None,
    gamets: float,
) -> tuple[Claim, BeliefInstance, Evidence, Grudge | None]:
    """A crime_witnessed event's cascade: always a belief (witness()), a
    grudge (suffer_harm(), rule 12) only when the witness IS the victim.

    victim_id is caller-supplied, never inferred (T2.3's lesson): a witness
    is a self-victim exactly when victim_id == witness_id; None or any
    other id means bystander -- belief only, no grudge, matching
    suffer_harm()'s own documented self-victim invariant.
    """
    claim, belief, evidence = self.witness(
        claim_id=claim_id,
        belief_id=belief_id,
        evidence_id=evidence_id,
        kind=crime_type,
        slots={
            "perpetrator_id": perpetrator_id,
            "victim_id": victim_id,
            "location_id": location_id,
        },
        canonical_event_key=...,  # the crime_witnessed event's own key
        witness_id=witness_id,
        gamets=gamets,
    )
    grudge = None
    if victim_id == witness_id:
        grudge = self.suffer_harm(
            holder_id=witness_id,
            target_id=perpetrator_id,
            grievance_type=crime_type,
            source_belief_id=belief.id,
            evidentiary_strength=1.0,  # firsthand witnessed, T2.3: caller-supplied not derived
            gamets=gamets,
        )
    return claim, belief, evidence, grudge
```

`evidentiary_strength=1.0` is a first-cut constant, in keeping with T2.3's
"caller-supplied, never derived" doctrine for this field elsewhere in the
codebase (rules 14/15/17/18/12 all take it as a caller input already) — a
richer mapping (e.g. discounting for crime severity or detection state)
is a follow-on tuning question, not a blocker for this cut.

This function calls exactly two existing, already-rule-gated methods in
sequence. It registers no rule, adds no store, and changes no existing
call site's behavior.

## 4. Listener/transport: extend the existing endpoint, not a new one

Following every prior slice's precedent (`docs/design/
chronicle-bridge-vendor-markup-out.md`, `-avoidance-out.md`,
`-hydration-out.md` all extend `/whiterun/events` or add sibling
poll/ack pairs rather than one-off routes), `crime_witnessed` extends the
**existing** `POST /whiterun/events` contract instead of adding a new
route — `_handle_events()` (`listener.py`) is already generic (it just
validates against the `GameEvent` model and shells out to `chronicle
inject`); only the contract and the injection helper are death-specific
today:

1. `adapters/skyrim/contracts/chronicle-bridge.openapi.yaml`'s `GameEvent`
   schema grows a `crime_witnessed` variant (discriminated on
   `event_type`, or a second oneOf branch) with `witness_id`,
   `perpetrator_id`, `crime_type`, `victim_id` (optional), `location_id`
   (optional) — regenerate `models.py` per this directory's own README.md
   instructions, the same regen step every prior contract change already
   uses.
2. `listener.py`'s `_inject_death_event()` generalizes into a small
   dispatch (or gets a `crime_witnessed`-specific sibling,
   `_inject_crime_witnessed_event()`) that builds the
   `crime_type`/`perpetrator_id`/`victim_id`/`location_id` payload and
   shells out through the same `python -m chronicle inject ... --origin-kind
   adapter` path — unchanged discipline, no new write mechanism.
3. No new poll/ack pair is needed (unlike hydration/avoidance/vendor-markup,
   which are Chronicle-to-game *writes*); `crime_witnessed` is a game-to-
   Chronicle *event*, same direction and same one-shot POST shape as
   `npc_died` already uses.

This is buildable today, independent of whether the C++ side ever produces
a real `crime_witnessed` POST — exactly like death-extraction's Python-only
cut landed before its C++ half.

## 5. Non-goals / explicitly unscoped (report 30's two open C++ questions)

This design's Python-only first cut stops at the listener boundary
described in §4. It deliberately does **not** scope, and this doc should
not be read as quietly resolving, either of report 30's open C++-side
questions:

- **Witness-set real-data uncertainty.** Report 30's F2: the mechanics of
  reading `RE::ExtraPlayerCrimeList`/`RE::Crime::actorsKnowOfCrime` via
  plain `extraList.GetByType<T>()` are confirmed hook-free, but *whose*
  `extraList` vanilla actually populates this on is unconfirmed — the one
  real-world implementation found (`Skyrim-Crime-Extensions`) sidesteps the
  question by manually attaching its own bookkeeping to witness NPCs rather
  than reading a vanilla-populated instance off the player. Report 30 calls
  this "a real gap, not a solved question" that blocks writing
  implementation code, resolvable only by a live-game `extraList` dump.
  Nothing in this doc depends on that being resolved, but nothing in this
  doc resolves it either.
- **Event-detection R&D-spike tier.** Report 30's F4: real event-level
  crime-alarm hooking (as opposed to polling `GetCrimeValue()`'s bounty/
  infamy value, which report 30 downgraded to routine) requires raw
  `SKSE::GetTrampoline()` detours onto unnamed internal functions
  (`SendCrimeFactionAlarm`, etc.) with no Address-Library-backed symbol —
  confirmed by reading a real mod's actual hook-installation code, not
  inferred. This stays R&D-spike-tier, unchanged from report 29/30's own
  verdict, and is out of scope for this doc entirely.

Put plainly: **this doc defines what Chronicle does with a `crime_witnessed`
event once one arrives, and extends the transport contract so one legally
could arrive — it does not attempt to make the game actually produce one.**
That remains a separate, still-open spike, exactly as report 30
recommended keeping it separate from the routine bounty-value polling
slice.

## 6. Summary of what this cut is / isn't

**Is:** a `victim_id` field added to the already-existing `CrimeWitnessed`
event; a new `Driver.crime_witnessed()` orchestration method that reuses
`witness()` (always) and `suffer_harm()`/rule 12 (only when the witness is
the crime's own victim) with zero new rules; an extension of the existing
`/whiterun/events` contract and its listener handler to accept the new
event kind, mirroring `npc_died`'s existing shape; unit tests exercising
both cascade branches (bystander: belief + reputation hit, no grudge;
self-victim: belief + grudge) the same way `test_rules.py`'s rule-12 tests
already do for `suffer_harm()`.

**Isn't:** anything on the C++/ChronicleBridge plugin side that actually
detects or emits a real `crime_witnessed` event from a live game — that
stays gated behind report 30's two open questions, unscoped here on
purpose.
