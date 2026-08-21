# Architecture

## Deployment target

Native Linux host for Chronicle (the Python service, dashboard, and later
the local-LLM/TTS tiers), with Skyrim SE/AE running under Proton on the
same machine, talking to Chronicle over localhost HTTP. SKSE64 and native
C++ DLL plugins run fine under Proton (Steam Deck-proven) — the bridge
plugin's HTTP calls originate inside the Proton prefix but pass through to
the native Linux service transparently over localhost; neither side needs
to know the other is in a different environment. Game files/saves live
under the Proton prefix (`steamapps/compatdata/<appid>/pfx/...`), directly
visible to Chronicle's Linux-side Python — convenient for staging things
like the voice bank later, though `adapters/skyrim/`'s sync layer still
prefers HTTP over file-polling IPC regardless (`docs/decisions/0005-sync-handshake.md`).

v0.1 needs none of this — it's headless (`chronicle/` + `dashboard/`, pure
Python + browser) and runs anywhere, including a MacBook. The Proton/SKSE
seam only becomes relevant at v0.2.

**Game version pin** (`docs/decisions/0008-game-version-pin.md`): Skyrim
SE/AE **1.6.1170 + SKSE64 2.2.6**, not the 1.7.99 patch (shipped
2026-08-20) — every AI-NPC framework and every dependency in the pin
still targets 1.6.1170 as of this writing. Revisit per the ADR's trigger,
not preemptively.

## Event-sourced core

`chronicle/events.py` defines an append-only `EventLog`. Every fact that
enters the system — an NPC death, a witnessed crime, a rumor heard — is an
immutable `Event`. All derived state (belief facets, rumor content,
grudge/obligation ledgers, reputation scores) is computed by folding over
the log, never mutated in place. This gives us, for free:

- **Replayability** — rerun the log to reproduce any world state exactly.
- **Debuggability** — the dashboard's causality timeline is just "show me
  the events that produced this belief."
- **Headless testability** — scenarios seed the log and assert on derived
  state; no running game required (see `scenarios/`).

`chronicle/` must stay engine-agnostic: no Skyrim-specific types or imports.
Everything that knows about Skyrim lives in `adapters/skyrim/`.

## The three tiers

See `docs/vision.md` for the *why*. Architecturally:

- **Math tier** — runs every tick over all ~1,000 NPCs. Deterministic
  propagation (who hears what, from whom, via encounter rolls sampled from
  NPC schedules), decay, and opinion/reputation drift. No LLM calls.
- **Local-LLM tier** — a small local model runs semantic mutation only for
  ~30 high-centrality "gossip hub" NPCs, on a much lower cadence than the
  math tier. Produces new/mutated rumor content and belief updates that get
  folded back into the event log as ordinary events, so tier 1 stays the
  only thing that has to run every tick.
- **Conversation tier** — a large LLM handles player-facing dialogue. It
  reads rendered belief state as context and writes back structured
  evidence (what the player told this NPC, what the NPC just revealed) as
  new events. This is the seam that has to interoperate with Mantella/CHIM
  — see below.

Tier interface is event-in, event-out at every boundary: no tier holds
authoritative state itself. The event log is the only source of truth.

## Timeline branching (save/reload)

Skyrim's save topology is a DAG, not a line: players save, die, reload,
and roll back constantly. Every event carries a branch key
`(save_uuid, generation)`; reloading an earlier save forks a new
generation rather than rewriting or deleting anything, and state
derivation is a path traversal from the root along one branch's lineage to
its head — not a fold over the entire log. See
`docs/decisions/0004-timeline-branching.md` (the branch/DAG model) and
`docs/decisions/0005-sync-handshake.md` (the SKSE-shim/service handshake
that keeps writes fenced to the right branch). `chronicle/events.py`
implements the branch-aware log; the co-save shim that produces
`save_uuid`/`generation` values lives in `adapters/skyrim/`.

## The FormID rule

Skyrim FormIDs are load-order-relative: a FormID's upper bits encode the
owning plugin's position in the active load order, so adding, removing, or
reordering mods invalidates any raw FormID stored externally. **Never
persist a raw FormID in Chronicle's event log or derived state.** Store a
composite key instead — plugin name plus the static local FormID offset —
and resolve it against the current load order (the same way SKSE's
`ResolveFormId` does) only at the point of use in `adapters/skyrim/`. A
raw-FormID leak would silently corrupt events after any load-order change,
in a way indistinguishable from a genuine timeline-fork bug — treat this
rule as load-bearing for `0004-timeline-branching.md`, not just a style
preference.

## Substrate Abstraction Layer (SAL)

Chronicle's domain events are defined against a generic Python provider
interface, not against any single mod's API. Two providers implement it,
both under `adapters/skyrim/`:

- **Reference implementation — the standalone bridge**: powerofthree's
  Papyrus Extender (MIT, open-source, already a required dependency of
  SkyrimNet itself) plus an open-source SKSE HTTP/WebSocket bridge. Built
  first; Chronicle's tests and scenarios target this provider by default.
- **Optional adapter — SkyrimNet**: low-latency, direct Papyrus/C++ event
  access when SkyrimNet is installed. Pinned hard to one specific
  SkyrimNet beta and its declared Public API version.

`chronicle/` never imports either provider directly. See
`docs/decisions/0003-substrate-choice.md` for the risk rationale and the
amendment that inverted which provider is primary.

### SkyrimNet adapter isolation rules

If/when the SkyrimNet adapter is built, three rules apply, all sourced to
documented integrator pain (`docs/research/10-skyrimnet-health.md`):

- **Startup version handshake.** The adapter declares the exact SkyrimNet
  Public API version it was built against and checks it at startup; on
  any mismatch it refuses to run with a clear error, rather than degrading
  silently or crashing later on a missing symbol (the failure mode
  IntelEngine hit when a required export wasn't present in an older
  build).
- **All `Register*` calls isolated in one adapter module, with contract
  tests.** `RegisterEvent`, `RegisterPackage`, `RegisterDecorator`,
  `RegisterAction`, and their `*ByUUID` variants go through a single
  module Chronicle owns, tested against the pinned API version's
  contract. An upstream SkyrimNet API break is then a one-file fix, not a
  Chronicle-wide refactor.
- **Init-ordering guard.** The adapter registers only after SkyrimNet has
  finished its own initialization — never speculatively early. SeverActions
  v3.0.1 hit a startup deadlock from registering decorators before
  SkyrimNet's own systems were ready; this guard exists specifically to
  avoid reproducing that.
- **Never redistribute the DLL.** Chronicle integrates against SkyrimNet's
  documented public API at arm's length only; the closed binary is never
  bundled or shipped with Chronicle.

## Injection seam (Mantella/CHIM)

Chronicle doesn't render its own dialogue. Belief/rumor/relationship state
gets serialized into prompt context that Mantella- or CHIM-style dialogue
mods consume, and player statements captured by those mods get turned back
into Chronicle events. This seam is intentionally thin and lives in
`adapters/skyrim/`, downstream of the SAL above.

## Data ownership layers and inspectability

Chronicle's belief/rumor/grudge/obligation/reputation state (not yet
built — the event log is the only piece that exists today) is organized
into five ownership layers, only the first of which is objective:
canonical event log → claim/variant store → subjective belief store →
social state store → narrative/query layer. See
`docs/decisions/0006-data-ownership-layers.md` for the full rationale, the
record shapes, and the load-bearing **sparse-graph rule** (never a
complete N×N relationship matrix over ~1,000 NPCs) and
**observer-local-reputation rule** (never one global score).

Every derived social outcome must be explainable via evidence-chain
drill-down — who believes it, from what evidence, through whom, since
when, why it changed. See `docs/decisions/0007-inspectability.md`; this is
both a schema constraint and the dashboard's core query.

## Build order

From `docs/research/08-social-sim-literature-v2.md` §9, promoted into the
project plan:

**Build first**: canonical events, claims, variants, belief instances, and
evidence chains; Gossamer's witness/reflection/propagation/decay gossip
loop; sparse relationship histories (City of Gangsters-style); bounded
memory and mutation (fuzzy-trace theory's verbatim/gist split, source
monitoring, simplified ACT-R activation); obligations and grudges as typed
records; observer-local reputation (Beta distribution, subjective logic).

**Add next**: Daley–Kendall/Maki–Thompson/SIHR-style rumor-state
transitions; Deffuant–Weisbuch and Friedkin–Johnsen updates for continuous
attitudes (faction sentiment, not event facts); face-threat scoring for
accusations/requests/refusals; batch story sifters; Dwarf-Fortress-style
long-term memory summarization.

**Defer**: full norm emergence; general-purpose logic programming; anomaly
detection; prospective drama management; **LLM reflection or dialogue
integration** — the local- and conversation-LLM tiers above come only
after the math tier and belief-facet store are proven headless in
`scenarios/`, per the staged plan every hybrid-architecture report
(`docs/research/03-...`) and this literature report both converge on.

## Hydration-override seam

When a Skyrim cell loads, vanilla NPC AI packages/schedules take over by
default. The hydration seam is where Chronicle overrides that: on cell
attach, it checks whether any NPC in the cell has Chronicle-driven state
(a grudge that should change their patrol, a rumor that should send them
somewhere) and injects a runtime AI package override before vanilla
schedule logic runs. Also lives in `adapters/skyrim/`.
