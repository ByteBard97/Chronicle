# ChronicleBridge

The Chronicle project's SKSE plugin (`adapters/skyrim/README.md`'s "only
place in the repo allowed to know Skyrim exists"). **First slice only**
(`docs/design/chronicle-bridge-spatial-streamer.md`): samples every actor
currently outdoors in Whiterun at ~1Hz and pushes their positions to a
listener running on the Chronicle host (`adapters/skyrim/listener/`). No
event sinks, no hydration, no save/reload sync yet.

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

Not yet implemented (see the `TODO` in `src/plugin.cpp`): the outbound
target currently defaults to `127.0.0.1:8765`, which only works if
Chronicle runs on the same machine as the game. Once Skyrim runs on its
own machine, this needs to read the Chronicle host's real LAN IP from an
INI file (the conventional `Data/SKSE/Plugins/ChronicleBridge.ini`
pattern) rather than a hardcoded default.

## Filling in the named-cast identity table

`src/IdentityMap.cpp`'s `kNamedCast` table is deliberately empty --
filling it in with guessed FormIDs would be worse than the generic
fallback catching them honestly (see that file's comment). Once the
plugin can run: check `ChronicleBridge.log` (in Skyrim's SKSE logs
folder) for the FallbackIdentity strings it logs for actors near the
player, cross-reference the plugin+local-id pairs against Chronicle's
actual named cast (`chronicle/fixtures/whiterun_relationships.py`), and
add entries.
