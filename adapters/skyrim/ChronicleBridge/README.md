# ChronicleBridge

The Chronicle project's SKSE plugin (`adapters/skyrim/README.md`'s "only
place in the repo allowed to know Skyrim exists"). Two slices so far:

- **Slice 1** (`docs/design/chronicle-bridge-spatial-streamer.md`):
  samples every actor currently outdoors in Whiterun at ~1Hz and pushes
  their positions to a listener running on the Chronicle host
  (`adapters/skyrim/listener/`).
- **Slice 2** (`docs/design/chronicle-bridge-death-extraction.md`): sinks
  `RE::TESDeathEvent` and POSTs a discrete death event to the same
  listener's `/whiterun/events`. Compiles cleanly against the real
  CommonLibSSE-NG headers (see that doc's §5) but has never run against a
  live game — do not treat it as verified beyond "compiles and matches
  the design."

No hydration, no save/reload sync yet — both real future work.

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

`src/IdentityMap.cpp`'s `kNamedCast` table is deliberately empty --
filling it in with guessed FormIDs would be worse than the generic
fallback catching them honestly (see that file's comment). Once the
plugin can run: check `ChronicleBridge.log` (in Skyrim's SKSE logs
folder) for the FallbackIdentity strings it logs for actors near the
player, cross-reference the plugin+local-id pairs against Chronicle's
actual named cast (`chronicle/fixtures/whiterun_relationships.py`), and
add entries.
