# ChronicleBridge

The Chronicle project's SKSE plugin (`adapters/skyrim/README.md`'s "only
place in the repo allowed to know Skyrim exists"). Seven slices landed
as of 2026-08-27:

- **Slice 1** (`docs/design/chronicle-bridge-spatial-streamer.md`):
  samples every actor currently outdoors in Whiterun at ~1Hz and pushes
  their positions to a listener running on the Chronicle host
  (`adapters/skyrim/listener/`).
- **Slice 2** (`docs/design/chronicle-bridge-death-extraction.md`): sinks
  `RE::TESDeathEvent` and POSTs a discrete death event to the same
  listener's `/whiterun/events`.
- **Slice 3** (`docs/design/chronicle-bridge-hydration-out.md`):
  `HydrationPoller` polls the listener's `GET /whiterun/hydration` every
  ~8s and writes changed relationship ranks into live
  `RE::BGSRelationship` records — **the first WRITE path in
  ChronicleBridge**; slices 1 and 2 only ever read/observed game state.
  Scope is deliberately narrow: it only updates an *existing*
  relationship record (`RE::BGSRelationship::GetRelationship()` found
  something); a pair with no authored vanilla relationship is skipped,
  never created (a real save-integrity risk this project doesn't yet
  understand well enough to take on — see that design doc's §3c).
- **Slice 4** (`docs/design/chronicle-bridge-avoidance-mutagen-out.md`):
  `AvoidancePoller` + a Mutagen-authored patcher content pack
  (`tools/chronicle-patcher/`) drive Flee-package avoidance between 171
  real NPC pairs (all 19-choose-2 of the named cast), gated by a
  per-pair global. Real FormIDs deployed via a real patcher run, no
  placeholders left in `AvoidanceGlobals.cpp`.
- **Slice 5** (`docs/research/28-vendor-price-hook-address-library-spike.md`):
  `VendorPriceHook.{h,cpp}` — the first vtable/UI hook, swapping
  `RE::VTABLE_BarterMenu`'s `PostCreate` and the barter menu's
  `UpdateItemCardInfo` callback to multiply prices for a marked-up
  vendor.
- **Slice 6** (`docs/design/chronicle-bridge-crime-witness-out.md`):
  Python-only cut of the crime-witness cascade (`Driver.
  crime_witnessed()`); no C++ event sink yet — `docs/research/29`/`30`
  found no clean `TESCrimeEvent`-style sink exists, and identified
  poll-based bounty/witness reads (no hook needed) as the likely path,
  with one live-game check still open (which actor's `extraList`
  vanilla populates `ExtraPlayerCrimeList` on).
- **Slice 7** (`docs/design/chronicle-bridge-diegetic-evidence-out.md`):
  `EvidencePoller.{h,cpp}` — belief/evidence state spawns as a real
  authored `MiscItem` in the world at a believer's live position, gated
  on `BeliefInstance.confidence`.

The named-cast map (`IdentityMap.cpp`'s `kNamedCast`) covers 19 of
Whiterun's 28 live-captured NPCs (`2f27cc8`), up from 1 at slice-1 time.

The whole tree (all 7 slices, 24 files) builds clean together
(previously only spot-checked individually), and the compiled DLL plus
a real 171-pair patched ESP are deployed into a live dev install
(`~/Games/ChronicleDev`, correct load order). **None of the seven
slices has ever run against a live game.** "Compiles and matches the
design" and "verified safe in an actual play session" are different
claims; only the first is true for any of this as of the last update to
this file. Slices 3, 4, 5, and 7 in particular mutate persistent
save-relevant game state or live UI and must not be treated as tested
until someone confirms them manually in a real play session — see
`docs/design/chronicle-bridge-verification-runbook.md`.

No save/reload sync yet — ChronicleBridge targets a single
developer-designated live run with no multi-save branch awareness (the
same trust model since slice 1); `chronicle/sync.py`/`chronicle fork`
exist and are tested but nothing wires them into a live ChronicleBridge
session yet (`docs/design/chronicle-sync-cli-integration.md`).

Wire format: `adapters/skyrim/contracts/chronicle-bridge.openapi.yaml` --
if you change the payload shape, update that file first; the C++
serialization (`src/OutboundClient.cpp`) is hand-written to match it, not
generated (see that file's header comment for why).

## Build requirements (Windows, native -- no Proton/Wine)

- **Visual Studio 2022** (Community edition is fine) with the "Desktop
  development with C++" workload.
- **CMake** 3.25.1+.
- **vcpkg** -- clone it, run `bootstrap-vcpkg.bat`, and set a `VCPKG_ROOT`
  environment variable pointing at it.
- **Ninja** (vcpkg or a standalone install; `CMakePresets.json` uses it as
  the generator).

## Building

```
cmake --preset release
cmake --build build/release
```

To have the built DLL copied straight into a mod manager's mods folder,
set one of these environment variables before configuring:

- `SKYRIM_MODS_FOLDER` -- e.g. MO2's `mods/` directory; the DLL lands in
  `<that>/ChronicleBridge/SKSE/Plugins/`.
- `SKYRIM_FOLDER` -- Skyrim's install root directly (its `Data/` folder is
  the target).

## Runtime configuration

`Data/SKSE/Plugins/ChronicleBridge.ini` (`src/Config.cpp`) overrides the
outbound target -- create it next to the DLL once Skyrim runs on a
different machine than Chronicle:

```ini
[General]
Host=192.168.1.50
Port=8765
SharedSecret=whatever-the-listener-was-started-with
```

Any key left out (or the file itself being absent) falls back to the
built-in default for that field (`127.0.0.1:8765`, no shared secret) --
so a fresh install with no ini yet behaves exactly as before this
existed. `SharedSecret` must match whatever the listener was started
with (`--shared-secret`, `adapters/skyrim/listener/listener.py`) or every
POST gets rejected with 401.

## Filling in the named-cast identity table

`src/IdentityMap.cpp`'s `kNamedCast` table has 19 entries as of
2026-08-26 (grown from a single `ysolda` entry this session, sourced
from a real live Whiterun snapshot,
`adapters/skyrim/listener/whiterun-positions.json`) -- but it is never
guessed: every entry is a real observed `(pluginName, localFormId)`
pair, cross-referenced against Chronicle's own fixture cast
(`chronicle/fixtures/whiterun_schedule.py`), never a hardcoded hex value
typed from memory (see that file's own comment for why -- a wrong guess
would silently resolve to the wrong NPC, worse than the generic fallback
catching it honestly). To add more: check `ChronicleBridge.log` (in
Skyrim's SKSE logs folder) for the `FallbackIdentity` strings it logs
for actors near the player, cross-reference the plugin+local-id pairs
against Chronicle's fixture cast, and add entries the same way.
`adapters/skyrim/listener/listener.py`'s `NAMED_CAST_NPC_IDS` and
`chronicle/tests/test_fixtures.py`'s `NAMED_CAST_NPC_IDS` both hand-mirror
this same 19-entry set -- update all three together (there is no shared
source of truth between C++ and Python for this table).
