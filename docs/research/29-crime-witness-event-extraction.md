# Crime/witness event extraction — verifying a secondhand AI's claims against CommonLibSSE-NG headers and primary sources

**Document File ID:** docs/research/29-crime-witness-event-extraction.md
**Date:** 2026-08-27

## TL;DR

An external AI's 7 claims about Skyrim/Oblivion crime mechanics and a proposed
`TESCrimeEvent` ChronicleBridge slice were checked against a local
CommonLibSSE-NG header checkout, UESP, and Nexus/mod primary sources. **No
`RE::TESCrimeEvent` type exists anywhere in CommonLibSSE-NG** — this was the
load-bearing technical claim (item 7) and it is wrong as stated. The engine
does have internal `BSTEventSink<Bounty::Event>`, `BSTEventSink<AssaultCrime::Event>`,
and `BSTEventSink<MurderCrime::Event>` types (confirmed via RTTI/VTABLE
signature offsets), but CommonLibSSE-NG has never wrapped them into public,
subscribable `RE::` headers the way `TESDeathEvent` is wrapped — they exist
only as raw addresses used internally by the game's own achievement/misc-stat
counters (`_MiscStatIncrementer`, `_BountyToMiscStatHandler`). This directly
confirms and sharpens `docs/research/22`'s own already-filed finding: crime/
bounty has no `ScriptEventSourceHolder`-registrable sink, and the only path
in is a reverse-engineered vtable/function hook — the same risk category as
report 26/28's vendor-price-hook work, not the `DeathEventSink` pattern.

Of the 7 claims: **1 is essentially correct** (initial-vs-locked-in witnesses,
terminology aside), **2 is refuted** (Responsibility is Oblivion-only, absent
from Skyrim), **3 is verified but the transfer argument is weak** (the mod is
real, but Oblivion's Papyrus-native crime-witness hooks are architecturally
unlike Skyrim/SKSE's closed engine), **4 is overstated** (conflates a real
but narrow vanilla Easter-egg mechanic with a "Reputation system" that is
actually third-party mod territory), **5 is real but mischaracterized** (the
mod exists, but the cause is non-persistent-reference unloading, not a
"Papyrus crashes" bug, and the fix is an SKSE C++ plugin, not console
commands), **6 is independently corroborated** by this project's own report
15, and **7's core recommendation is wrong on the mechanism** (no clean
event-sink exists) but right on the underlying idea (crime-witness data is
real, present in the engine's `Crime` struct, and extractable — just not for
free).

## Findings

### 1. [REFUTED — mechanism, VERIFIED — architecture claim] `TESCrimeEvent` does not exist; crime *data* does

Direct grep of `/home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG`
for `TESCrimeEvent` returns zero matches, in headers or sources. There is no
`RE::TESCrimeEvent`, no `RE::BSTEventSource<TESCrimeEvent>`, nothing
registerable via `RE::ScriptEventSourceHolder` the way `DeathEventSink.h`
sinks `RE::TESDeathEvent`.

What does exist:

- **`RE/C/Crime.h`** defines a real `RE::Crime` struct (`sizeof == 0x78`),
  reverse-engineered from the game binary. It has a genuine witness list:

  ```cpp
  struct Crime {
      ...
      BSTArray<ActorHandle>   actorsKnowOfCrime;  // 28 — the witness list
      ...
      TESFaction*             crimeFaction;       // 60
      mutable BSReadWriteLock lock;               // 68
  };
  ```

  Everything else in the struct is unlabeled `unk` fields — no `crimeType`,
  no per-witness "has reported" flag, no timestamp, no location. The witness
  *set* is real and directly matches item 7's `witness_id` idea; nothing else
  in the payload wishlist (`crime_type`, `detection_level`, per-witness
  report status) is exposed by this struct as reverse-engineered so far.

- **`RE/E/ExtraPlayerCrimeList.h`** exposes `BSSimpleList<Crime*>* crimes` —
  how a `TESObjectREFR` (the player) accumulates its own `Crime*` list.

- **`RE/P/PlayerCharacter.h`** and **`RE/T/TESFaction.h`/`.cpp`** expose the
  bounty-*value* side: `CrimeGoldStruct{ witnessed, unwitnessed }`,
  `GetCrimeGoldValue`/`ModCrimeGoldValue`/`SetCrimeGoldValue` virtuals on
  `Actor`, and `TESFaction::ModCrimeGold`/`GetCrimeGold*` wrappers. These are
  real, callable functions (virtual-table slots, not raw signature-scanned
  addresses) — so the bounty *value* is easier to read/react to than the
  crime *event* is.

- **Internal-only crime event sinks exist but are unwrapped.** `Offsets_RTTI.h`
  and `Offsets_VTABLE.h` contain real signature-scanned entries for:

  ```
  RTTI_BSTEventSink_Bounty__Event_
  RTTI___BountyToMiscStatHandler
  RTTI_BSTEventSink_AssaultCrime__Event_
  RTTI___MiscStatIncrementer_AssaultCrime__Event_
  RTTI_BSTEventSink_MurderCrime__Event_
  RTTI___MiscStatIncrementer_MurderCrime__Event_
  ```

  These prove the engine *internally* dispatches `Bounty::Event`,
  `AssaultCrime::Event`, and `MurderCrime::Event` through the standard
  `BSTEventSink` template — structurally identical machinery to
  `TESDeathEvent`. But CommonLibSSE-NG has not defined the `Bounty`,
  `AssaultCrime`, or `MurderCrime` namespaces/structs anywhere in `include/`
  — no `Event` struct layout, no `BSTEventSource<Event>::GetSingleton()`
  accessor. They are visible only as anonymous vtable addresses (used
  internally by `_MiscStatIncrementer`/`_BountyToMiscStatHandler`, the
  achievement/stat-tracking classes), not as a plugin-consumable header the
  way `DeathEventSink.h` consumes `TESDeathEvent`.

This is the precise resolution the task asked for. **`docs/research/22`'s own
already-filed TL;DR is correct and this pass corroborates it directly from
the header source**: "Crime accumulation is processed directly inside
faction structures and player character logic. Because no global crime sink
exists in ScriptEventSourceHolder, tracking bounty changes requires an
inline C++ function hook or detour... on `RE::TESFaction::ModBounty` or
`RE::PlayerCharacter::ModBounty`." The secondhand AI's claim 7 — that this is
a simple `TESCrimeEvent`-style sink hook — is wrong. The type doesn't exist
in the public surface; the closest analogues (`Bounty::Event` et al.) exist
only as unmapped internal vtables, a strictly harder starting point than
report 26/28's vendor-price hook (which at least had a documented,
Address-Library-backed `RE::VTABLE_BarterMenu`).

### 2. [VERIFIED, terminology loose] Initial vs. reported/locked-in witnesses

UESP and community sources (GameFAQs, gamerant "How to Get Rid of Bounties")
confirm: if detected committing a crime, killing every witness before any of
them reaches a guard (or before a guard who directly witnessed it) removes
the bounty entirely, with an on-screen confirmation. Once a witness reaches
a guard (or a guard is itself a witness), the bounty is "locked in" and
further witness-killing has no effect. Animals count as witnesses too.

UESP does not use the exact phrase "initial witnesses vs. reported
witnesses," but the underlying mechanic the claim describes — a
window during which witnesses can be silenced before the crime is
irrevocably reported — is real. **Verdict: [VERIFIED]**, modulo invented
terminology.

### 3. [REFUTED] Responsibility as a Skyrim mechanic

UESP (`Oblivion:Responsibility`) and Elder Scrolls Fandom both describe
Responsibility as a hidden 0–100 NPC attribute **specific to Oblivion**:
NPCs at 100 report crimes unconditionally (even undetected sneak-attack
kills trigger a bounty); 90–30 tolerate some theft and don't report unless
disposition drops; below 30 they ignore crimes and will fence stolen goods.
It also feeds Oblivion's Infamy-driven disposition penalty.

Skyrim removed the entire Attributes system (Strength/Intelligence/etc. and,
with it, most hidden per-NPC 0–100 stats of this kind) in favor of a
simplified detection/alarm/faction-flag model (`FACTION_DATA::Flag` values
like `kIgnoresCrimes_Assult`/`kIgnoresCrimes_Stealing`/etc., confirmed
directly in `TESFaction.h`/`.cpp` above). There is no `Responsibility`
symbol, field, or actor value anywhere in the CommonLibSSE-NG headers, and
no source claims Skyrim retained it. **Verdict: [REFUTED]** — Responsibility
is Oblivion-only; Skyrim's witness/report gating is coarser (mostly
faction-level flags + detection state), not a per-NPC 0-100 dial.

### 4. [VERIFIED that a real mod exists — REFUTED that it's an Oblivion crime-hook precedent transferable to Skyrim]

`Crime has witnesses` (Nexus Oblivion mod 22894) and `Crime Has Witnesses -
Responsibility Tweak` (mod 33682) are both real, and the `KCWWQuest.forceWitnesses`
/ `ModCrimeGold` script-variable pattern described in the claim matches the
mod's own documentation (set `forceWitnesses` to 1 before an ad-hoc
`ModCrimeGold` call to force witness generation; it resets to 0 after).

But the transfer argument in the original claim is weak, and should be
called out plainly rather than repeated: Oblivion's crime system is exposed
almost entirely through **Papyrus-predecessor OBSE/vanilla script
functions** operating on **quest-script-visible globals** (`KCWWQuest` is a
quest script variable, directly settable from any script). Skyrim/SKSE's
crime system, by contrast, lives in unmanaged C++ structs (`RE::Crime`,
`ExtraPlayerCrimeList`) with no Papyrus-visible witness-forcing hook at all
— Skyrim's own Papyrus API exposes only `CrimeGold` getters/setters on
`Faction`, never anything witness-shaped. The Oblivion mod's trick works
*because* Oblivion's crime system was already script-native; Skyrim's isn't.
**Verdict: mod is real [VERIFIED], but it is a considerably weaker analogy
for SKSE/C++ work than the original framing implied** — it proves witness
mechanics were scriptable in a different, older, more script-exposed engine,
not that they're similarly reachable in Skyrim.

### 5. [OVERSTATED] "Reputation" tracking in vanilla Skyrim

Two things get conflated in the claim. What's real and vanilla:

- **`An enemy's gratitude`** (a genuine, UESP-documented vanilla mechanic,
  fixed multiple times by USSEP): killing an NPC can trigger a courier
  letter from one of that NPC's pre-authored *enemies* (per static
  relationship data, rank ≤ "foe"), sometimes with a gold reward. This is
  real, but it is a narrow, pre-authored, per-relationship-pair Easter egg —
  not a general reputation *system*.
- `setpcfame`/`setpcinfamy` console commands exist in Skyrim, evidence of
  leftover Fame/Infamy global variables from Oblivion, but community sources
  (GameFAQs, Nexus forums) agree these have **no meaningful vanilla gameplay
  effect** in Skyrim — Oblivion's Infamy→disposition→Responsibility pipeline
  was not carried forward.
- What actually matches the claim's fuller description ("4000 lines of
  dialogue arranged on a reputation spectrum," Companions recognizing
  fame/infamy for questline shortcuts) is the **"Skyrim Reputation" mod**
  (Nexus 22374 / 95269) — a third-party mod, not a vanilla mechanic.

**Verdict: [REFUTED as stated]** — the claim describes mod functionality as
if it were a vanilla "Reputation" system; the one genuine vanilla piece (An
enemy's gratitude) is real but far narrower (a handful of scripted
relationship pairs, not a morality score) than "reputation tracking...
detected vs. undetected crimes, faction reactions via courier notes" implies.

### 6. [VERIFIED, mechanism mischaracterized] Persistent Relations

"Persistent Relations - Generic NPC Amnesia Fix" (author zhitsak, Nexus,
requires Address Library) is a real SKSE C++ plugin for SE/AE/VR. Per its
own description: it monitors generic (non-persistent-reference) NPCs as they
unload, remembers the player's relationship rank with them, and restores it
on reload/unload cycles by storing the data in the save's co-save data.

Two specific parts of the claim don't hold up:

- It does **not** work "via console commands" — it's a native plugin writing
  to SKSE co-save data, invisible to the player.
- The stated cause is **not** "Papyrus's own relationship functions crash" —
  it's that vanilla non-persistent NPC references (`ObjectReference`s that
  aren't marked persistent) get their in-memory relationship state discarded
  when they unload, a reference-lifecycle/memory-management quirk, not a
  Papyrus VM crash.

**Verdict: [VERIFIED mod exists, REFUTED mechanism description]**. The
underlying lesson the claim wants to draw — vanilla Papyrus-side social
state is fragile and something needs to persist it more reliably outside
per-reference game memory — is directionally reasonable and consistent with
this project's own architecture (state lives in `chronicle`'s Python layer,
not in Papyrus globals), but the specific evidence cited to support it is
wrong on both mechanism and cause.

### 7. [BUILD-ON, independently corroborated] No existing mod does per-NPC witness memory / rumor propagation

This project's own `docs/research/15-skyrim-social-reactivity-mods.md`
already concludes, independently and before this task: "no prior Skyrim
reputation/rumor mod solves per-NPC belief with provenance or genuine rumor
propagation," and that the engine's own `Rumors` dialogue subtype is
"restricted to the innkeeper job faction" — never a general NPC-to-NPC path.
Report 17 adds that SkyrimNet's community IntelEngine plugin comes closest
with LLM-driven gossip chains, but that's LLM-authored freeform content, not
symbolic witness-tracked crime memory. **Verdict: [VERIFIED / independently
corroborated]** — this genuinely does appear to be open ground, on the
evidence of two independent research passes in this project plus this
session's targeted check.

## Recommendation

**Crime-witness extraction is R&D-spike-tier, not routine `DeathEventSink`-tier
work.** There is no `TESCrimeEvent` (or equivalent) sink to register with
`RE::ScriptEventSourceHolder`. A future ChronicleBridge "crime witnessed"
slice would need to choose one of:

1. **Function-hook the mutation points** — detour/hook
   `RE::Actor::ModCrimeGoldValue`/`SetCrimeGoldValue` (virtual, so a vtable
   swap works, similar in spirit to report 28's `RE::VTABLE_BarterMenu`
   trick) or `TESFaction::ModCrimeGold`. This tells you *that* a crime
   happened and its gold value/faction, on the main thread, synchronously —
   but not the witness list.
2. **Walk `RE::Crime::actorsKnowOfCrime` directly**, reached via
   `ExtraPlayerCrimeList::crimes` on the player's `TESObjectREFR` extra-data
   list, polled or read at the same hook point as (1). This is the one path
   that actually gets you the `witness_id` list the original recommendation
   wanted — but every field beyond that array is an unlabeled `unk` in the
   current CommonLibSSE-NG header, so `crime_type`/`detection_level`/
   timestamp would need either separate correlation (e.g., cross-reference
   with the faction/gold-delta from step 1) or their own reverse-engineering
   pass to identify the unk offsets.
3. **Reverse-engineer and wrap the internal `Bounty::Event`/`AssaultCrime::Event`/
   `MurderCrime::Event` sinks** found in the RTTI/VTABLE tables — the
   "correct-shape" answer structurally (a real `BSTEventSink`), but nobody
   has published the `Event` struct layout, so this is new reverse-engineering
   work, not a documented, ready-to-use header the way `TESDeathEvent` is.

Any of these is squarely in the same risk category `docs/research/22`
already flagged and `docs/research/26`/`28` already worked through for
vendor pricing — not a copy of the `DeathEventSink` pattern. Recommend
scoping a future "crime witness" slice as its own spike (most promising
starting point: option 2, since the witness array is already a known,
sized, reverse-engineered field — cheaper than options 1 or 3), explicitly
not bundled with any hydration/avoidance-tier next steps, exactly as report
26 scoped the vendor-price hook.

## Caveats

- The CommonLibSSE-NG checkout inspected is the vendored copy under
  `skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG`, not necessarily
  the exact copy vendored inside `adapters/skyrim/ChronicleBridge/` itself —
  if the two diverge in version, field offsets/struct completeness for
  `RE::Crime` could differ slightly, though the "no `TESCrimeEvent` exists"
  finding is a strongly-held negative (grep found zero occurrences of the
  string across the entire tree) and unlikely to be version-sensitive.
- `RE::Crime`'s unlabeled `unk` fields were not reverse-engineered as part of
  this pass — only the fact that they're unlabeled (and thus not
  ready-to-use) was established. A future spike could plausibly recover
  `crimeType` and a per-witness "reported" bit from these offsets by
  comparing against Papyrus's `Faction.GetCrimeGold`-family behavior or
  existing xEdit/CE structure dumps, which this pass did not attempt.
- UESP's `Skyrim:Crime` page itself returned HTTP 403 to direct fetch; the
  witness-locking mechanic (finding 2) is corroborated by search-engine
  summaries of that page plus independent GameFAQs/gamerant sources, not a
  direct primary-source read of the UESP article text.
- This report does not touch `adapters/skyrim/ChronicleBridge/` code, the
  `chronicle/` Python layer, or `docs/research/00-index.md`, per task
  instructions.
