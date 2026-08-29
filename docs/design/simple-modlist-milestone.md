# SimpleSkyrim: a stable debug modlist, and the first confirmed end-to-end live run

**2026-08-28.** This closes the M3 "does ChronicleBridge actually work in a
live game" question with a real, repeatable positive result, and leaves
behind `~/Games/SimpleSkyrim` as a lightweight, purpose-built debug
instance separate from NGVO (playthrough) and the retired ChronicleDev
mess from earlier the same night.

## What's proven, concretely

A 140-second continuous run in Whiterun, zero crashes, with the full
target stack loaded and active:

- **Base:** SKSE 2.2.6, Address Library, CrashLogger, USSEP (+ its 4
  required Creation Club masters: Fish, AdvDSGS, Curios, SurvivalMode)
- **Debug tooling:** devbench (the MCP/REST test-bench mod)
- **QoL:** SkyUI, PapyrusUtil, powerofthree's Papyrus Extender
- **Ours:** ChronicleBridge.dll + ChroniclePatcher.esp
- **The fix that made it possible:** Face Discoloration Fix
  (`FaceGenFixes.dll`, Exit-9B, v1.0.3) — see "The facegen crash" below.

With the listener running, ChronicleBridge's full HTTP loop was
confirmed live: `POST /whiterun/positions` → `204`, all four poll routes
(`hydration`/`avoidance`/`evidence`/`vendor-markup`) → `200`. The
listener's snapshot file filled with **27 live NPCs**, including
named-cast identity resolution (e.g. `sigurd`). This is the first time
any of this has been observed working end-to-end against a real,
running game.

## The facegen crash (the real blocker this session, not ChronicleBridge)

Every crash tonight after the initial USSEP/missing-master issue was
**`EXCEPTION_ACCESS_VIOLATION` in `BSFaceGenModel`/`BSFaceGenNiNodeSkinned`**,
~85 seconds into Whiterun — long enough for NPC heads to stream in.
Root cause (confirmed by isolation: pure vanilla held stable 110s;
USSEP+CC together crashed at 85s): **USSEP and the Creation Club NPCs
ship regenerated FaceGen data that can mismatch at runtime**, a
well-documented SSE modding issue, unrelated to Proton/Wine and
unrelated to ChronicleBridge. The community-standard fix is
**Face Discoloration Fix** (Exit-9B, github.com/Exit-9B/Face-Discoloration-Fix,
Nexus 42441) — a small SKSE-only plugin (no ESP, Address-Library-based,
works on 1.6.1170) that turns the mismatch into a logged warning +
regenerated face instead of a crash. Installed as a loose
`SKSE/Plugins/FaceGenFixes.dll`; confirmed loaded and its hooks
installed via its own log (`FaceGenManager.cpp: Installed hooks for
face discoloration fix`).

**If any future modlist on this project reintroduces USSEP or
Creation-Club NPCs and starts seeing a `BSFaceGen*` CTD ~60-90s into
a populated cell, this is almost certainly the same issue — install
Face Discoloration Fix before spending time on anything else.**

## Instance layout

`~/Games/SimpleSkyrim` — a portable MO2 instance, **hardlink-cloned**
from ChronicleDev (`cp -al`, near-zero extra disk: apparent size 26G,
real extra usage ~0), then stripped and repointed. Own Proton prefix:
`compatdata/4190904831` (`~/Games/launch-simpleskyrim-skse.sh`, same
`moshortcut://SKSE` pattern as the other instances).

**Known issue, not yet resolved:** launching through MO2's
`moshortcut://SKSE` was unreliable this session — sometimes the whole
MO2 process silently died before spawning anything, for reasons not
diagnosed (possibly related to the first-run prefix creation race also
seen with ChronicleDev's own MO2 launch). All verification in this doc
was done via a **direct `skse64_loader.exe` launch** (bypassing MO2/
usvfs entirely — `/tmp/direct-launch-simple.sh`, not yet promoted into
the repo) with mods deployed as **loose files** into `Stock Game/Data`
rather than through MO2's virtual filesystem. This proves the mod set
itself is sound; it does not prove MO2 will reliably launch it. Next
person to pick this up should either (a) debug MO2's launch reliability
directly (compare against NGVO's/ChronicleDev's working `moshortcut`
launches, check for a first-run vs warm-run difference), or (b)
promote the direct-loader + loose-deploy pattern into a proper repo
script if MO2 turns out not to be worth fighting for a debug-only
instance.

## What's still loose-deployed vs MO2-managed

Everything currently in `Stock Game/Data` was copied there by hand
during this session's testing (see the loose-deploy commands in this
session's transcript) to work around the MO2 launch issue above. The
MO2 mod folders under `~/Games/SimpleSkyrim/mods/` and `profiles/
Default/modlist.txt`/`plugins.txt` were kept roughly in sync but are
**not the source of truth right now** — the loose `Data/` files are.
Before trusting MO2 again for this instance, reconcile: either clear
`Data/` back to vanilla and prove MO2 deploys the same set correctly,
or accept the loose-file approach as the instance's actual management
method and update `modlist.txt` to match reality (or drop it/document
it as unused).

## Next mods to add (per the original ask: "quality of life... anything
that could help us debug it")

Not yet added, candidates for the next pass: a save-cleaning/testing
QoL mod, a console command enhancer (if any beyond vanilla), and
whatever the live-test harness (`docs/design/live-test-harness.md`)
needs once it's pointed at this instance instead of ChronicleDev.
