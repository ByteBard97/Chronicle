---
date: 2026-08-27
sources:
  - local CommonLibSSE-NG header/source checkout at
    /home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG
    (RE/T/TESFaction.h + .cpp, RE/P/PlayerCharacter.h, RE/A/Actor.h,
    RE/E/ExtraPlayerCrimeList.h, RE/Offsets_VTABLE.h)
  - github.com/fireundubh/LibFire, src/Papyrus/PapyrusPlayerCharacter.cpp
    (public GitHub repo, fetched via `gh api`) — a real, shipped Papyrus
    native-function library; fireundubh is an established, credible SKSE
    plugin author (Modern Brawl Bug Fix, Ordinator patches, etc.)
  - github.com/Monitor221hz/Skyrim-Crime-Extensions, src/hook.cpp,
    src/hook.hpp, src/RE/Crime.h (public GitHub repo, GPL-3.0, fetched via
    `gh api`) — a real, in-progress SKSE plugin specifically built to
    extend Skyrim's crime/witness/alarm system
  - GitHub code search (`gh api search/code`) on the exact symbols this
    project's own report 29 already surfaced:
    `actorsKnowOfCrime`, `ModCrimeGoldValue`, `GetCrimeValue crimeGoldMap`,
    `ExtraPlayerCrimeList`, `Bounty::Event AssaultCrime`,
    `GetCrimeGoldValue TESFaction`
  - docs/research/29-crime-witness-event-extraction.md (this doc's direct
    predecessor and premise)
  - docs/research/28-vendor-price-hook-address-library-spike.md (the
    template this follow-up spike was asked to repeat)
topic: "Locating real prior art for crime/bounty/witness extraction, for the pinned 1.6.1170 build — does report 29's R&D-spike verdict downgrade the way report 26's vendor-price verdict did?"
status: filed
---

# Crime/Witness Extraction: Prior-Art Spike — A Split Verdict, Not a Clean Downgrade

**Document File ID:** docs/research/30-crime-witness-prior-art-spike.md

## TL;DR

Report 29 classified crime/witness extraction as R&D-spike-tier, on par with
the vendor-price hook before report 28 found DynamicPrices-SKSE's real
source and downgraded it. **This pass ran the same play and found real,
shipped, open-source prior art for two of the three pieces report 29
identified — but the verdict splits instead of downgrading cleanly.**

**Piece 1 — current bounty/infamy VALUE per faction: fully downgraded to
routine-buildable, zero hooks needed at all.** `RE::PlayerCharacter::
GetCrimeValue()` returns a plain, non-virtual, offset-based (`RelocateMember`)
struct with two fully-named `BSTHashMap`s — `crimeGoldMap` (per-faction
`{violentCur, nonViolentCur, nonViolentInfamy, violentInfamy}`, all named
floats, no `unk` fields) and `stolenItemValueMap`. (`GetCrimeValue()` itself
resolves via `REL::RelocateMember` — a hardcoded, SE/AE/VR-branched struct
offset, reverse-engineered, but by CommonLibSSE-NG upstream, long since
stabilized and already load-bearing for `TESFaction::GetCrimeGold()`'s own
implementation; this pass adds no *new* reverse-engineering on top of it.)
This is exactly the same architecture already backing `TESFaction::GetCrimeGold()`/
`GetCrimeGoldViolent()`/`GetCrimeGoldNonViolent()` in this project's own
vendored header. **`fireundubh/LibFire` (a real, shipped Papyrus
native-function library by an established SKSE author) already reads this
exact field in production** to implement `IsPlayerWanted`/`IsPlayerInfamous`/
`FindPlayerWantedByFactions` — plain iteration over the hashmap, no event,
no hook, no trampoline. This is pollable today with the identical
`HydrationPoller`/`AvoidancePoller` timer-and-diff pattern this project
already uses.

**Piece 2 — the witness list: the read mechanics need no hook, but this pass
found a real gap in *whose* `extraList` carries the data — flagged, not
resolved.** `RE::ExtraPlayerCrimeList` (the wrapper holding
`BSSimpleList<Crime*>* crimes`) is a plain `BSExtraData` entry — the generic
`actor->extraList.GetByType<T>()`/`Create<T>()`/`Add()` mechanics are real,
hook-free, and confirmed by direct use in `Skyrim-Crime-Extensions`.
`RE::Crime::actorsKnowOfCrime` (the witness array) is already named and
public in this project's own CommonLibSSE-NG header. **But reading
`Skyrim-Crime-Extensions`' full source (not just its first 150 lines) shows
its own author does not read a vanilla-populated `ExtraPlayerCrimeList` off
the player at all — its `AssignCrimeReporter()` *manually*
`BSExtraData::Create<ExtraPlayerCrimeList>()`s a fresh one and attaches it
to a chosen witness NPC's `extraList` as the mod's own custom
signaling/bookkeeping hack**, receiving the actual `Crime*` from the
engine via its hooked `SendCrimeAlarm*` functions (F4's raw detours), not
by polling anyone's extra-data. This real implementation neither confirms
nor refutes report 29's original assumption ("`ExtraPlayerCrimeList` is how
the *player* accumulates its own crime list") — it simply never needed to
test that assumption, because it gets its `Crime*` pointers from a hook
instead. **Net effect: the extra-data read mechanics are proven safe and
hook-free in general, but whether polling `player->extraList.
GetByType<ExtraPlayerCrimeList>()` on a timer actually yields the vanilla
per-crime witness data — as opposed to coming back empty because the
engine populates it differently or only transiently — remains unverified
by any source this pass found**, report 29's included. This is a small,
concrete, live-game-checkable question (attempt a crime, dump the player's
`extraList` contents), not a large spike, but it is a real open item, not
a solved one.

**Piece 3 — detecting a crime as a discrete, instantaneous *event* (as
opposed to periodically polling the two data structures above): remains
genuinely R&D-spike-tier, and this pass's strongest, most decisive finding
is *why*.** Reading `Skyrim-Crime-Extensions`' actual hook installation
code shows it does **not** use report 28's downgrade pattern (a documented
vtable-slot swap). It uses **raw `SKSE::GetTrampoline().write_call<5>()`/
`write_branch<5>()` detours onto hand-identified, unnamed internal engine
functions** — `REL::RelocationID(36430, 37425)` at `+0x4E2`/`+0x4CD` with
IDA-derived comments like `Character__UpdateFactionCrimeGold_1405F7D20` and
`SendCrimeFactionAlarm_14064FF50`. These are not CommonLibSSE-NG symbols,
not vtable slots, not anything with a name in any public header — they are
literal numeric offsets into disassembled, unnamed internal functions that
the mod's author found by reading the game binary in IDA/Ghidra. **This is
the real thing report 29 was worried about, confirmed to exist in the wild
exactly as feared**, and it is categorically harder than the vendor-price
vtable-swap: no Address Library symbol softens it, and getting these numbers
right for the pinned 1.6.1170 build would mean redoing that disassembly
work from scratch (the repo's checked-in RelocationIDs are the author's own
findings, not portable proof for a different pinned build without
independent verification).

**One correction to report 29's own recommendation, found along the way:**
report 29 filed hooking `Actor::ModCrimeGoldValue` (option 1) in the same
risk bucket as walking `actorsKnowOfCrime` cold — implicitly, "still needs
a hook, still risky." That undersold it. `ModCrimeGoldValue` is confirmed
(`RE/A/Actor.h:380`) to be a **named, documented virtual function at a known
vtable slot (`0xB6`)**, and `RE::VTABLE_Actor` is a real, 10-entry,
Address-Library-backed array (`include/RE/Offsets_VTABLE.h:2142`). Hooking
it would be `RE::VTABLE_Actor[0]` + `write_vfunc(0xB6, ...)` — **the exact
same low-risk, no-reverse-engineering-needed vtable-swap pattern report 28
validated for `RE::IMenu::PostCreate()`/`RE::VTABLE_BarterMenu`**, not a raw
trampoline detour onto an unnamed function. Nobody in the wild appears to
have actually built this specific hook (no GitHub hit found it), but the
ingredients are all present and documented, unlike piece 3's alarm-dispatch
hooks.

## Findings

**[F1] [VERIFIED, production-proven] Bounty/infamy value polling needs no
hook — `PlayerCharacter::GetCrimeValue()` is a real, non-virtual,
fully-named, already-shipped-in-a-real-mod data structure.**

```cpp
// RE/P/PlayerCharacter.h
struct CrimeGoldStruct {
    float violentCur;        // 00
    float nonViolentCur;     // 04
    float nonViolentInfamy;  // 08
    float violentInfamy;     // 0C
};
struct StolenItemValueStruct {
    std::int32_t unwitnessed;  // 0
    std::int32_t witnessed;    // 4
};
struct CrimeValue {
    BSTHashMap<const TESFaction*, CrimeGoldStruct>       crimeGoldMap;       // 00
    BSTHashMap<const TESFaction*, StolenItemValueStruct> stolenItemValueMap; // 30
};
[[nodiscard]] inline CrimeValue& GetCrimeValue() noexcept { /* RelocateMember, offset 0x3E0/0x3E8/0x9D0 depending on VR/SE-AE */ }
```

Every field is named, no `unk`. `TESFaction::GetCrimeGold()`/
`GetCrimeGoldViolent()`/`GetCrimeGoldNonViolent()`/`GetInfamy()`/
`GetStolenItemValueCrime()` in this project's own vendored `TESFaction.cpp`
already read straight from this struct via `PlayerCharacter::GetSingleton()`.
**`fireundubh/LibFire`'s `PapyrusPlayerCharacter.cpp` reads this exact field
in a real, shipped plugin**:

```cpp
for (const auto& [first, second] : player->GetCrimeValue().crimeGoldMap) {
    auto total = second.nonViolentInfamy + second.violentInfamy;
    if (total > 0.0f) { results.push_back(const_cast<RE::TESFaction*>(first)); }
}
```

No hook, no event sink, no trampoline — just a `GetSingleton()` call and a
hashmap iteration. This is directly pollable on a timer using this
project's existing `HydrationPoller`/`AvoidancePoller` pattern (snapshot the
map each tick, diff against last-seen values per faction, push a Chronicle
event on change). **Verdict: routine-buildable, no reverse-engineering,
independently confirmed in a real shipped plugin.**

**[F2] [VERIFIED, mechanism confirmed — REFUTED, report 29's framing of
`ExtraPlayerCrimeList` as needing a hook] Reading the witness list needs no
hook either — it is plain `BSExtraData`.**

```cpp
// RE/E/ExtraPlayerCrimeList.h
class ExtraPlayerCrimeList : public BSExtraData {
    BSSimpleList<Crime*>* crimes;  // 10
};
```

`BSExtraData` entries are read the same way this project's own code already
reads other extra-data types (e.g. `Skyrim-Crime-Extensions`' own
`extraDataList->GetByType<ExtraLinkedRef>()`, structurally identical to
`GetByType<ExtraPlayerCrimeList>()`). Report 29 filed this under "option
2... reached via `ExtraPlayerCrimeList::crimes` on the player's
`TESObjectREFR` extra-data list, polled or read at the same hook point as
(1)" — implying it needed to piggyback on a hook. **It does not.** It can be
read cold, on its own timer tick, independent of any hook, exactly like
`RE::Crime`'s already-public `actorsKnowOfCrime` field:

```cpp
// RE/C/Crime.h (this project's own vendored header)
struct Crime {
    BSTArray<ActorHandle> actorsKnowOfCrime;  // 28 — real, named, public
    TESFaction*            crimeFaction;      // 60 — real, named, public
    mutable BSReadWriteLock lock;              // 68
    // everything else: unlabeled `unk`
};
```

**[F3] [MIXED — two independent third-party reverse-engineering attempts
exist, and they substantially disagree] Beyond `actorsKnowOfCrime`/
`crimeFaction`, no offset on `RE::Crime` should be trusted without a live
check — but the qualitative claim "more is extractable than the official
`unk` fields admit" is now corroborated twice, independently.** This pass
found a *second* community fork beyond `Monitor221hz`'s — `JerryYOJ/
Status-Indicator-Framework-SKSE`'s `src/RE/Crime.h` — and reading it
reveals the two forks agree on almost nothing except the two fields the
official CommonLibSSE-NG header already gets right:

| offset | official header | Monitor221hz fork | JerryYOJ fork |
|---|---|---|---|
| 0x00 | `unk64` | `unk64` | `refCount` (u32) |
| 0x04 | (inside unk00) | (inside unk00) | `crimeType` (`PackageNS::CRIME_TYPE`) |
| 0x08 | `unk64` | `victim` (`ActorHandle`) | `sceneHandle` (`ObjectRefHandle`) |
| 0x0C | (inside unk08) | `perpetrator` (`ActorHandle`) | `criminalHandle` (`ActorHandle`) |
| 0x28 | `actorsKnowOfCrime` | `actorsKnowOfCrime` ✓ agree | `actorsKnowOfCrime` ✓ agree |
| 0x58 | `unk64` | `unk64` | `bountyAmount` (u32) |
| 0x60 | `crimeFaction` | `crimeFaction` ✓ agree | `crimeFaction` ✓ agree |
| 0x68 | `unk32` + `lock` (both `//68`, self-inconsistent) | same self-inconsistency | `crimeEstablished` (bool) at 0x68, `lock` cleanly at 0x6C (internally consistent) |

Reading both together **downgrades confidence in either source's specific
offsets/types** (a real `victim`/`ActorHandle` and a real
`sceneHandle`/`ObjectRefHandle` at the same 0x08 are not the same claim,
even though both point at "something ref/actor-identifying lives here") —
but **raises confidence that a `crimeType`, a `bountyAmount`, and
identity-shaped fields genuinely exist in the low/mid offsets report 29
and this project's own vendored header treat as opaque `unk64`s**, since
two independent authors converged on "there's real structured content
around 0x00–0x0C and 0x58" from two different reverse-engineering efforts.
JerryYOJ's version is also the more internally self-consistent of the two
(no offset collision at 0x68, unlike Monitor221hz's), which is *some*
evidence of more careful work, not proof of correctness. **Verdict: treat
"a real `crimeType`/bounty/identity payload exists below `actorsKnowOfCrime`"
as a corroborated, promising lead worth a live-game verification spike;
treat any specific field name, offset, or type from either fork as
unverified and possibly wrong** until checked against a live memory dump
for the pinned 1.6.1170 build.

**[F4] [DECISIVE] Real event-level crime-alarm hooking, done by a real mod
built for exactly this purpose, uses raw trampoline detours onto unnamed
internal functions — not a documented vtable slot.** `Skyrim-Crime-
Extensions`' `SendCrimeAlarmHook::Install()` and `UpdateFactionBounty::
Install()`:

```cpp
REL::Relocation<std::uintptr_t> targetAssault{ REL::RelocationID(36430, 37425), REL::Relocate(0x5D4, 0x5A9) };
// comment: Character__sub_1405DE870+5D4 call SendCrimeFactionAlarm_14064FF50
auto& trampoline = SKSE::GetTrampoline();
SKSE::AllocTrampoline(70);
_SendCrimeAlarmAssault = trampoline.write_call<5>(targetAssault.address(), SendCrimeAlarmAssault);
```

Five separate call sites, each a raw `RelocationID` + byte offset into an
unnamed function, sourced from the author's own IDA disassembly (comments
throughout the file are literal cross-reference dumps: `Up p
Actor__CaughtTrespassing_1405DF630+2AE call SendCrimeFactionAlarm_14064FF50`).
None of `SendCrimeFactionAlarm`, `UpdateFactionCrimeGold`, or the internal
`RaiseAlarm` dispatcher have any presence in CommonLibSSE-NG's public
headers — grep of this project's vendored checkout confirms zero matches
for any of these three names. **This is precisely the reverse-engineering
tier report 29 flagged as the worst case (option 3: "reverse-engineer and
wrap the internal `Bounty::Event`/`AssaultCrime::Event`/`MurderCrime::Event`
sinks"), now confirmed to be exactly what a real author had to do to get
event-level fidelity.** Unlike report 28's vendor-price finding, there is no
"actually it was just a documented vtable slot" twist here — the twist runs
the other way.

**[F5] [CORRECTS REPORT 29] `Actor::ModCrimeGoldValue` is a named, vtable-
slotted virtual, not an unmapped function — hooking it would be a
vtable-swap, same risk tier as report 28's `IMenu::PostCreate` finding.**

```cpp
// RE/A/Actor.h:380
SKYRIM_REL_VR_VIRTUAL void ModCrimeGoldValue(TESFaction* a_faction, bool a_violent, std::int32_t a_amount);  // 0B6
```

```cpp
// RE/Offsets_VTABLE.h:2142
constexpr std::array<REL::VariantID, 10> VTABLE_Actor{ REL::VariantID(260538, 207511, 0x16ce888), ... };
```

`0xB6` is a real vtable index, `VTABLE_Actor[0]` is a real,
Address-Library-ID-backed relocation already sitting in this project's own
checkout. Hooking `ModCrimeGoldValue` would be `REL::Relocation<std::uintptr_t>
vtbl{ RE::VTABLE_Actor[0] }; vtbl.write_vfunc(0xB6, &Hook);` — structurally
identical to `DynamicPrices::Install()`'s `write_vfunc(0x2, ...)` on
`VTABLE_BarterMenu`, which report 28 already validated as
`[BUILD-ON]`-tier. Report 29's recommendation lumped this in with "any of
these is squarely in the same risk category" as the raw-detour options;
this pass finds that's not quite right — **this specific hook target is
meaningfully cheaper than options 2/3 in report 29's own list**, though
nobody has been found actually shipping it (no GitHub hit uses
`ModCrimeGoldValue` as a hook target, only as a header declaration), so
treat this as "ingredients confirmed present," not "pattern proven in the
wild" the way F1/F2 are.

## Recommendation

**Split verdict, and it should stay split rather than being forced into one
bucket:**

1. **Bounty/infamy value tracking (does the player have an active
   bounty/how much/with which faction) — downgrade to routine-buildable,
   build now.** Poll `RE::PlayerCharacter::GetCrimeValue().crimeGoldMap`
   (and `stolenItemValueMap` for stolen-goods value) on the existing
   `HydrationPoller`/`AvoidancePoller` timer-and-diff cadence. Zero hooks,
   zero reverse-engineering, production-proven by `fireundubh/LibFire`.
   This alone covers a real, useful slice of report 29's original ask
   ("know when the player's bounty changes, with which faction, violent vs.
   not") without touching witness identity at all.

2. **Witness set — pollable in mechanics, but with one open question that
   needs a live-game check before committing an implementation, not just a
   header read.** The `extraList.GetByType<T>()`/`Create<T>()` mechanics
   are real and hook-free (F2), and `actorsKnowOfCrime` is genuinely public
   (official header, both third-party forks agree). But this pass could not
   confirm *whose* `extraList` vanilla populates `ExtraPlayerCrimeList` on
   — the one real implementation found repurposes the type as a custom
   witness-signal bucket on NPCs rather than reading a vanilla-populated
   instance off the player. **First concrete step before any polling code
   is written: a short live-game check** — commit a crime, dump the
   player's (and a witnessing NPC's) `extraList` contents, confirm which
   one (if either) actually carries a vanilla-populated
   `ExtraPlayerCrimeList`. This is a much smaller spike than report 29's
   original scope (one targeted live check, not a from-scratch hunt), but
   it is a real gap, not a solved question — don't schedule the polling
   implementation without it. Perpetrator/victim identity and any richer
   per-crime metadata (F3) should be treated as a nice-to-have bonus if the
   live check happens to reveal readable data there, not as a load-bearing
   assumption.

3. **Instantaneous "a crime just happened" event fidelity (vs. polling
   state that already reflects it) — stays R&D-spike-tier, unchanged from
   report 29, now with direct confirming evidence rather than an
   inference.** If poll-and-diff latency (same order as
   `HydrationPoller`'s 8-second tick) is acceptable — and for a
   grudge/reputation system reacting to accumulated player behavior, it
   plausibly is, the same way `HydrationPoller` doesn't need instant
   relationship-change notification either — **pieces 1+2 alone may make a
   dedicated event hook unnecessary for Chronicle's actual use case.** Only
   if true event-level fidelity turns out to be required should a hook be
   scoped, and if so: prefer **F5's `ModCrimeGoldValue` vtable-swap**
   (report-28-tier risk) over `Skyrim-Crime-Extensions`' raw alarm-dispatch
   detours (F4, genuine from-scratch reverse-engineering, unverified
   against the pinned 1.6.1170 build).

**Decisive answer to the task's framing question: this is not a clean
downgrade like vendor-price was, and forcing it into "routine-buildable"
across the board would be dishonest.** The headline data (bounty value,
witness set) turns out to need no hook at all, which is a bigger win than
report 29 anticipated — but the specific thing report 29's option 3 worried
about (an undocumented internal event sink requiring real
reverse-engineering) is now *confirmed to exist and be exactly that hard*,
via a real mod that had to do it. The honest scoping is: **build the
poll-based bounty+witness slice now, at HydrationPoller-tier risk; treat
true event-level crime hooking as a separate, still-open R&D spike, not
bundled with this pass's downgrade.**

## Caveats

- **F3's specific offsets/types are unverified by this pass and by
  CommonLibSSE-NG's own maintainers, and the two third-party sources found
  actively disagree with each other** on almost every field beyond
  `actorsKnowOfCrime`/`crimeFaction` — see the comparison table in F3. The
  *pattern* (more structured, non-`unk` content likely exists below
  `actorsKnowOfCrime`) is corroborated twice; no specific offset, name, or
  type from either fork should be relied on without a live memory check
  against the pinned 1.6.1170 build.
- **F2's core mechanism (generic `extraList.GetByType<T>()` reads/writes,
  no hook needed) is confirmed; which actor's `extraList` vanilla actually
  populates `ExtraPlayerCrimeList` on is not.** The one real implementation
  read in this pass sidesteps the question entirely (it manually creates
  and attaches the extra-data to witness NPCs as its own bookkeeping hack,
  rather than reading a vanilla-populated instance off the player) — so it
  neither confirms nor refutes report 29's original "the player accumulates
  its own crime list" assumption. This is the one item in this report that
  should block writing implementation code, not just ship-with-a-caveat: a
  short live-game dump of `extraList` contents (player and a witnessing
  NPC, after committing a crime) would settle it in one session.
- **F5's vtable-slot hook for `ModCrimeGoldValue` was not found built by
  anyone in the wild** — the ingredients (named virtual, known slot, real
  `VTABLE_Actor` Address Library entry) are all confirmed present in this
  project's own vendored headers, and the technique is structurally
  identical to report 28's validated `IMenu::PostCreate` swap, but this is
  this pass's own inference from header-reading, not a second real-world
  confirmation the way F1/F2 have. Flagged as "ingredients present," not
  "pattern proven twice."
- **`Skyrim-Crime-Extensions`' RelocationIDs (F4) are the author's own
  findings for whatever build they targeted** — the repo doesn't pin a
  specific game version in what this pass fetched, and reusing those exact
  numeric IDs against the pinned 1.6.1170 build without independently
  verifying them via Address Library would be unsafe; they're cited here as
  evidence of *what kind* of work event-level hooking requires, not as
  ready-to-use addresses.
- **No live game session was run in this pass** — F1 and F2's "no hook
  needed" claims rest on reading real shipped source (`LibFire`) and
  cross-referencing header struct layout/BSExtraData mechanics, the same
  confidence level report 28 reached before its own live-verification
  caveat; a short in-game smoke test (does `GetCrimeValue()` actually
  populate promptly after committing a crime; does `ExtraPlayerCrimeList`
  actually appear on the player's `extraList` when expected) would be the
  natural next step before scheduling implementation, exactly as report 28
  flagged for its own vtable-swap finding.
- This pass did not attempt to build, compile, or run anything, and did not
  touch `adapters/skyrim/ChronicleBridge/`, `chronicle/`, or
  `docs/research/00-index.md`, per task instructions.
