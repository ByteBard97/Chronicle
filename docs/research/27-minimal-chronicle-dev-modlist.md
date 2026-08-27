---
date: 2026-08-26
sources:
  - direct Nexus/GitHub verification this session (`gh api` for
    alandtse/CrashLoggerSSE and alandtse/devbench release history; web
    search for Nexus mod pages, blocked from direct fetch by Cloudflare
    403 — treated the same way `docs/research/25` already did, as a
    routine bot-block, not evidence against a page's existence)
  - `docs/decisions/0008-game-version-pin.md`, `docs/research/11-version-pin-and-transport.md`
  - `notes/skyrim-modlist-research/wabbajack-without-nexus-premium.md`,
    `.../ai-npc-dialogue-linux-compat.md` (owner's personal-playthrough
    research, reused here only for the Proton/MO2 mechanics that carry
    over)
  - `adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp` (read directly,
    not paraphrased)
  - `docs/research/25-devbench-skse-mcp-verification.md`,
    `docs/research/24-programmatic-esp-authoring.md`
topic: "a concrete, from-scratch, minimal MO2 mod list for Chronicle/ChronicleBridge development and debugging, distinct from the owner's NGVO and Apostasy/Tuxborn personal-playthrough installs"
status: filed
---

# A Minimal, From-Scratch MO2 Mod List for Chronicle Development

**Document File ID:** docs/research/27-minimal-chronicle-dev-modlist.md
**Date:** 2026-08-26

## TL;DR

An **8-third-party-mod, hand-built MO2 instance** (plus ChronicleBridge itself and
the base game — no Wabbajack gallery list) satisfies every constraint this project
actually has: the 1.6.1170/SKSE 2.2.6 pin, the 19-entry named-cast FormID table in
`IdentityMap.cpp`, and DevBench-driven in-game verification. **Downgrading to
1.6.1170 is still both necessary and available in 2026** — Bethesda's 1.7.99
(2026-08-20) is still the Steam default, and both the Steam-console
`download_depot` method and at least three community patcher tools (two of them
released *after* 1.7.99 specifically to handle this) remain live and maintained.
**One finding revises this task's own stated premise**: `IdentityMap.cpp` does
*not* only reference `Skyrim.esm`/`HearthFires.esm` — 2 of its 19 named-cast
entries (`idolaf_battle_born`, `lillith_maiden_loom`) currently resolve, at
runtime in NGVO, against `unofficial skyrim special edition patch.esp` (USSEP) as
`GetFile(0)`'s owning plugin. Reading `RE::TESForm::GetFile()`/`GetLocalFormID()`
in the local CommonLibSSE-NG checkout (see F3) shows this label is derived
per-session from whichever plugins actually touched the record where the snapshot
was taken — it is not necessarily "USSEP created this record," and it is not
something header-reading alone can fully settle. What *is* actionable: the
19-entry table was captured with USSEP active, so **this dev list should keep
USSEP active too**, to reproduce the exact environment the table was verified
against, rather than risk a different (unverified, possibly different-localFormId)
resolution for those two entries with USSEP absent. The recommended list is: USSEP
→ Address Library for SKSE Plugins → powerofthree's Papyrus Extender → PapyrusUtil
SE → SSE Engine Fixes → CrashLoggerSSE → DevBench → ChronicleBridge (the project's
own DLL) → SkyUI, all free, all currently 1.6.1170-compatible, small enough to
install by hand-clicking Nexus downloads on a free account in under an hour — no
Premium purchase and no Wabbajack needed at this mod count.

## Findings

**[F1] A downgrade step is still required and still available in 2026 — both the
depot method and dedicated patcher tools.** Nothing about ADR-0008's situation has
changed: 1.7.99 (shipped 2026-08-20) remains Steam's default, and the whole
native-plugin ecosystem (CrashLoggerSSE, DevBench, every AI-NPC framework) still
targets 1.6.1170 as its baseline, adding 1.7.99 support as a parallel build rather
than a replacement (see F5). Two live options:
- **Steam console `download_depot`.** `download_depot 489830 <depot> <manifest>`
  for the three 1.6.1170 depots (`489831`/`489832`/`489833`, exact manifest IDs in
  `docs/research/11-version-pin-and-transport.md`) — cross-platform since it's
  just the Steam client's own console, not a third-party binary. This is the
  method already named in ADR-0008's lock procedure and needs no new verification.
- **Dedicated downgrade patchers, now a small but active sub-ecosystem.** The
  **"Steam 1.7.99 → 1.6.1170 → 1.5.97 Best of Both Worlds Downgrade Patcher"**
  (Nexus #169962) applies BSDiff4 binary patches in place, preserves AE/Creation
  Club content, and was **last updated 2026-01-16** — i.e. already maintained
  through the January patch cycle, not a stale pre-1.7.99 tool; its own page notes
  it's "only supported for Windows, though Linux users have reported success"
  (i.e. runs under Proton with mixed reports, not a guaranteed Linux path).
  Two more recent, more narrowly 1.6.1170-scoped tools surfaced in this pass:
  **"SDT — Skyrim Downgrade Tool"** (Nexus #188916, tagline "Downgrade from ANY
  version to 1.6.1170") and **"Skyrim Downgrader"** (Nexus #188956) — both newer
  listings than Best of Both Worlds, suggesting the tooling is still being
  actively iterated on post-1.7.99, not abandoned. None of the three Nexus pages
  could be fetched directly (Cloudflare 403, the same routine block
  `docs/research/25` already documented — not evidence against existence; titles
  and metadata corroborated via search).
- **Recommendation: use `download_depot`** for this list specifically, since it's
  already the procedure ADR-0008 committed to and documented, is native to Steam
  (no extra Windows binary to run under Proton), and this dev instance's Stock-Game
  copy (F2) needs the raw depot files anyway. Keep Best of Both Worlds / SDT as the
  documented fallback if `download_depot` manifest IDs ever go stale.

**[F2] This list must NOT reuse NGVO's or Tuxborn's game copy — build a third, isolated
Stock-Game instance.** `notes/skyrim-modlist-research/wabbajack-without-nexus-premium.md`'s
"Stock Game / Game Root" pattern (every modern Wabbajack list copies the base game into
its own MO2 folder, never touching the Steam install) is exactly the mechanism this dev
list needs too, for the opposite reason the owner's personal lists use it: NGVO and
Apostasy/Tuxborn are free to track whatever runtime their own lists specify, while
*this* instance's entire reason to exist is staying locked to 1.6.1170 + SKSE 2.2.6
indefinitely. Build it as `~/Games/ChronicleDev/` (sibling to the existing
`~/Games/NGVO` and `~/Games/Tuxborn`), with its own private copy of the 1.6.1170 depot
files (via `download_depot`, F1) as the `Game Root`, its own MO2 portable instance
pointed at that copy, and its own Proton prefix (a new non-Steam-game shortcut, same
`GE-Proton10-14` already installed and working for NGVO per `tools/launch-ngvo-skse.sh`).
This guarantees a Steam auto-update to NGVO's or Tuxborn's copy (or an accidental Steam
Play button click, the exact failure mode ADR-0008's lock procedure exists to prevent)
can never touch this dev instance's files.

**[F3] `IdentityMap.cpp`'s two USSEP-attributed entries are real and reproducible,
but the mechanism is subtler than "USSEP owns those records" — verified against
CommonLibSSE-NG source, not just the code comment.** Direct read of
`adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp` (`kNamedCast`, lines 48–68):
17 of 19 entries use `"Skyrim.esm"` or `"HearthFires.esm"` as `pluginName`, matching
this task's stated "unmodified official masters only" premise — but two do not:
`{"unofficial skyrim special edition patch.esp", 0x01a689, "idolaf_battle_born"}`
and `{"unofficial skyrim special edition patch.esp", 0x10e2b6, "lillith_maiden_loom"}`.
Cross-checking the raw snapshot these came from
(`adapters/skyrim/listener/whiterun-positions.json`, read directly, not just the
comment describing it) confirms both IDs verbatim: `"unofficial skyrim special
edition patch.esp:01a689"` → Idolaf Battle-Born, `"...:10e2b6"` → Lillith
Maiden-Loom. Both local IDs sit inside the *same contiguous `0x01a6xx` block* as
several `Skyrim.esm`-attributed neighbors (`0x01a680` Anoriath, `0x01a684`
Fralia, `0x01a685` Olfina, `0x01a68c` Lars) — i.e. these are not USSEP-native
FormIDs in USSEP's own allocation range (contrast the same snapshot's six
"Whiterun Guard" entries, which *do* carry USSEP-native IDs like `0x037058` and
`0x1000f7`, clearly outside the vanilla actor block — genuine USSEP-created
records). Reading `RE::TESForm::GetFile()`/`GetLocalFormID()` in the local
CommonLibSSE-NG checkout
(`/home/geoff/projects/skyrim-re-toolkit/type-importer/vendor/CommonLibSSE-NG/include/RE/T/TESForm.h`,
lines 273–301) shows `ResolveFormRef`'s `form->GetFile(0)` reads index 0 of the
form's `sourceFiles` array — populated at runtime from whichever plugins actually
touched that specific record in *this* load order/session — and
`GetLocalFormID()` derives its masked local ID from that same file's
`compileIndex`. **This means the `pluginName`/`localFormId` pair this table
hardcodes for these two entries is a function of the exact load order the
snapshot was captured under (NGVO, USSEP active, 2026-08-24), not necessarily
"USSEP created or owns the base record."** Whether index 0 reflects the true
originating master or an override-touched entry was not fully resolved by header
reading alone in this pass — that would need either a live before/after capture
with USSEP removed, or deeper CommonLibSSE-NG/engine-internals research, neither
of which was attempted here. **What is safe to act on regardless of that open
question: this dev modlist should keep USSEP active, because that is the exact
environment the current 19-entry table was verified against.** Building this list
*without* USSEP would put the two entries in an unverified state — at best a
silent identity-resolution miss (falling through to `FallbackIdentity()`'s
`plugin:formid` string instead of `idolaf_battle_born`/`lillith_maiden_loom`), at
worst a different, also-untested `(pluginName, localFormId)` pair if `GetFile(0)`
resolves differently once USSEP no longer touches those records. Either way, this
revises this task's brief, which stated the table depends only on
`Skyrim.esm`/`HearthFires.esm` — that premise doesn't hold for 2 of the 19
entries as currently observed, and should be flagged to the owner directly rather
than silently corrected.

**[F4] HearthFires.esm needs no special enabling step — it ships inside the AE base
install, not as separate purchasable/optional content.** Anniversary Edition bundles
the three legacy DLCs (Dawnguard, Hearthfire, Dragonborn) directly into the base
`Data/` folder as of the AE re-release; they are not part of the opt-in Creation Club
catalog. Any 1.6.1170 depot pull (F1/F2) already contains `HearthFires.esm` on disk,
and MO2 auto-lists all masters found in its configured `Data/` folder in the left
pane, checked by default. The only failure mode worth watching for is a Stock-Game
copy assembled from an incomplete depot set (missing the DLC-bearing depot) — verify
`HearthFires.esm` is physically present in `ChronicleDev/Game Root/Data/` once the
depot pull finishes, before assuming it's fine.

**[F5] Address Library for SKSE Plugins (Nexus #32444) is still the correct, current
dependency name, and CommonLibSSE-NG's own posture treats it as necessary-but-not-
sufficient — consistent with what ADR-0008 and `docs/research/11` already
concluded.** This project's own prior research (`docs/research/11`, "Address Library
alone does NOT save plugins... only handles function addresses, not class layout")
already settled the substantive technical question; this pass found nothing that
changes it. Address Library ships two builds on its Nexus page (the legacy SE
"All-in-one" for 1.5.97, and a separate AE/1.6+ build) — ADR-0008's pin table already
specifies "v11+" for the AE build, which is what this list needs. (Nexus page fetch
blocked by the same Cloudflare 403 pattern noted throughout; the two-build split and
version-independence design are corroborated by the CommonLibSSE-NG/community
descriptions found via search and consistent with this project's own already-cited
sourcing in `docs/research/11`.)

**[F6] CrashLoggerSSE (alandtse) is real, current, and its release history shows the
exact "1.7.99 added, 1.6.1170 kept" pattern this whole pin strategy depends on.**
Verified directly via `gh api repos/alandtse/CrashLoggerSSE/releases`: **v1.25.0**
(published 2026-08-21, one day after the 1.7.99 patch) whose changelog reads
verbatim *"Features: support Skyrim AE 1.7.99 (#42)"* — an *addition*, not a
replacement, matching the same pattern this project's own research already
documented for CrashLoggerSSE's dependency `SSE Engine Fixes` and for DevBench
itself (`docs/research/25`, v1.15.0 "support Skyrim AE 1.7.99" as an additive
release). The prior release, **v1.24.0** (2026-06-28), predates 1.7.99 entirely and
is therefore unambiguously a 1.6.1170/AE-only build if a maximally conservative pin
is wanted. **Recommendation: install the current latest release (v1.25.0 or newer)**
— alandtse's own multi-year pattern across CrashLoggerSSE, DevBench, and SSE Engine
Fixes is additive multi-version support in one build, not version-gated forks, so
the newest release should still work on 1.6.1170; if a future release's changelog
ever reads as a *migration* rather than an *addition* (dropping old-runtime support
outright), fall back to pinning v1.24.0 specifically.

**[F7] DevBench's MO2 install is exactly like any other SKSE-plugin mod — no special
handling.** Per `docs/research/25` (already verified in depth: real repo, GPL-3
core + MIT integration glue, `127.0.0.1:8920` for SE/AE) plus this pass's
confirmation of its install instructions: it installs like any Data-folder SKSE
plugin (drop into MO2 as a normal mod, or extract to `Data/` directly), with
optional config at `Data/SKSE/Plugins/devbench/config.json` (bind address fixed to
loopback, start port defaults to 8920, auto-advances if taken). **Correction to
`docs/research/25`'s own framing, which assumed a separate Windows box reached over
SSH:** this project's actual deployment target (`docs/architecture.md`, "Skyrim SE/AE
running under Proton on the same machine" as Chronicle's Linux service) means
DevBench's `127.0.0.1:8920` is reachable **directly** from Chronicle's own Linux
Python process with no SSH tunnel at all — the Proton prefix's loopback socket is the
same machine's loopback, full stop. The SSH-tunnel scenario in `docs/research/25`
only applies if Chronicle's controlling process and the Skyrim/DevBench process are
ever split across two physical machines (e.g. testing from a laptop against the
Windows build machine) — not this list's actual use case.

**[F8] SkyUI remains the standard, near-zero-risk QoL choice in 2026, and it's the
only QoL mod this list needs.** SkyUI (Nexus #12604) requires only SKSE (already a
foundation of this list) — it does not use Address Library or any native-code
version dependency, so it carries none of the patch-day fragility every other mod in
this list is built around avoiding. It touches only the inventory/menu UI layer, has
zero interaction surface with `IdentityMap.cpp`'s named-cast NPCs or their AI
packages, and is a dependency of a large fraction of the wider ecosystem (including,
per `notes/skyrim-modlist-research/ai-npc-dialogue-linux-compat.md`, both Apostasy
and Tuxborn) — familiar territory, not a new risk surface. **Deliberately not
recommending anything beyond this one QoL mod**: a Papyrus log viewer is
unnecessary since the Proton prefix's `Documents/My Games/Skyrim Special
Edition/Logs/Script/` directory is already directly visible to the Linux host
(`docs/architecture.md`'s own point about save/log visibility) — `tail -f` covers
this need without installing anything. An in-game console/dev-tools mod is
redundant with DevBench, which already exposes console-command execution
programmatically (`docs/research/25`, §4) — installing a second console-enhancer
mod would be adding a mod "because it's popular," exactly what this task asked to
avoid.

**[F9] No population/city-overhaul or NPC-replacer risk exists in this list by
construction, but the constraint is worth stating explicitly for future sessions.**
None of the 9 mods recommended here touch NPC base records, AI packages, or
`Whiterun.esm`-adjacent cell edits — the closest thing to a risk is USSEP itself
(F3), and USSEP's own stated scope is bugfixes, not content redesign, and it is
*already* the plugin `IdentityMap.cpp` depends on, not a new risk this list
introduces. **Flag for any future session extending this list**: never add a city
population mod (e.g. "Populated Cities," "Immersive Citizens," any Whiterun NPC
replacer/AI overhaul) without first checking it against all 19 `kNamedCast` entries
in `IdentityMap.cpp` — such a mod could re-point, delete, or renumber any of
Braith/Carlotta/Amren/etc.'s FormIDs, silently breaking identity resolution the same
way an absent USSEP would (F3), except worse (no fallback path if the base record
itself is gone).

## Recommendation

**Build a new MO2 instance, `~/Games/ChronicleDev/`, from scratch, isolated from
NGVO and Apostasy/Tuxborn, with exactly this mod list:**

| # | Mod | Nexus / Source | Role | Load-order note |
|---|-----|-----------------|------|-------------------|
| — | Skyrim SE/AE **1.6.1170** | Steam `download_depot` (F1/F2) | Game version pin (ADR-0008) | Stock-Game copy, not the Steam-managed install |
| — | **SKSE64 2.2.6** | skse.silverlock.org | Script extender loader | Launch only via `skse64_loader.exe` |
| 1 | **Unofficial Skyrim Special Edition Patch (USSEP)** | Nexus #266 | Bugfix patch — **load-bearing**, not optional (F3) | Near the top, standard USSEP position |
| 2 | **Address Library for SKSE Plugins** (AE build, v11+) | Nexus #32444 | Function-address resolution for every native plugin below | No plugin/ESP; order-independent |
| 3 | **powerofthree's Papyrus Extender** | Nexus #22854 | ADR-0003's SAL reference-implementation dependency | No plugin; order-independent |
| 4 | **PapyrusUtil SE 4.6** | Nexus #13048 | ADR-0008 pin | No plugin; order-independent |
| 5 | **SSE Engine Fixes**, Part 1, v6.1.1/6.2 (1.6.1170 build) | Nexus #17230 | ADR-0008 pin — stability substrate | Part 1 installs as a normal MO2 mod; **Part 2 must be extracted straight into the game's `Data/` folder** (it's a non-SKSE loose-file/`.ini` component the mod's own docs say bypasses MO2's virtual filesystem) — with this list's Stock-Game layout that means `ChronicleDev/Game Root/Data/`, not through MO2's Install Mod flow |
| 6 | **CrashLoggerSSE** (current release, F6) | Nexus #59818 / github.com/alandtse/CrashLoggerSSE | Crash logging for dev iteration | No plugin; order-independent |
| 7 | **DevBench** (current release) | Nexus #181326 / github.com/alandtse/devbench | In-game MCP/REST test bench (F7) | No plugin; near bottom |
| 8 | **ChronicleBridge** (this project's own `.dll` + `.ini`) | built locally (`.claude/windows-build-machine.md`) | The thing being tested | No plugin; **bottom of the left pane**, wins any conflict |
| 9 | **SkyUI** | Nexus #12604 | Only QoL mod in the list (F8) | Standard SkyUI position, after USSEP |

Nine real mods plus the DLC-bearing base game — small enough to install by hand,
clicking through Nexus's free-account manual-download flow in well under the
"hundreds of clicks" problem `notes/skyrim-modlist-research/wabbajack-without-nexus-premium.md`
documents for large Wabbajack lists. **No Wabbajack, no Jackify, and no Nexus
Premium purchase are needed for this list** — that tooling exists to solve a
large-list problem this deliberately small list doesn't have.

**Build order:**
1. Pin the game version first (F1/F2): pull the three 1.6.1170 depots into
   `~/Games/ChronicleDev/Game Root/` via `download_depot`, matching ADR-0008's
   already-documented manifest IDs. Verify `HearthFires.esm` is present (F4).
2. Install SKSE64 2.2.6 into that Game Root.
3. Set up a fresh, portable MO2 instance pointed at that Game Root — not a copy of
   NGVO's instance, not sharing its Proton prefix. Add a new non-Steam-game Proton
   shortcut for it (reuse the already-installed, checksum-verified `GE-Proton10-14`
   per `tools/launch-ngvo-skse.sh`'s header comments) with its own compat-data
   prefix.
4. Download and install mods 1–9 in the table above, in that order, via MO2's
   normal "Install Mod" flow (drag-and-drop archive or "Add from URL"). None of
   these are large files; a free Nexus account with manual clicking is a non-issue
   at this count.
5. Run LOOT once (cheap, harmless, and confirms nothing is flagged), even though a
   list this size barely needs sorting: the only two ESPs in the whole list are
   USSEP's and SkyUI's, and both have well-known, stable positions LOOT gets right
   automatically. Do not hand-tune further.
6. Drop `ChronicleBridge.dll` and its `.ini` into their own MO2 mod folder
   (mirroring how mod 7/8 above are installed — a plain `SKSE/Plugins/` drop, no
   ESP), placed at the very bottom of the left pane per this project's own existing
   convention for winning file conflicts (see `notes/skyrim-ai-modlist-plan.md`'s
   note on SkyrimNet's own bottom-of-pane placement for the same reason, applied
   here to Chronicle's own plugin instead).
7. Launch via MO2's `moshortcut://` mechanism, the same pattern
   `tools/launch-ngvo-skse.sh` already established and fixed (unquoted title,
   `waitforexitandrun`) — write a `launch-chronicledev-skse.sh` twin once the
   instance exists, pointed at `ChronicleDev` instead of `NGVO`.
8. Verify DevBench is listening (`Test-NetConnection`-equivalent or a plain `curl
   127.0.0.1:8920/api/tools` from the same Linux machine, no tunnel needed per F7)
   and that ChronicleBridge's own log shows it loaded, before running any of
   `docs/design/chronicle-bridge-verification-runbook.md`'s steps.

## Caveats

- This pass could not directly fetch any Nexus mod page (Cloudflare 403 on every
  attempt) — every specific version/date claim about a Nexus-hosted mod (Address
  Library, USSEP, po3's Extender, PapyrusUtil, SSE Engine Fixes, SkyUI, CrashLogger,
  DevBench) is corroborated via web search snippets and/or this project's own
  already-verified prior research (ADR-0008, `docs/research/11`, `docs/research/25`),
  not a direct primary-source read of the Nexus page itself. The two GitHub-hosted
  facts (CrashLoggerSSE's and DevBench's actual release/changelog history) *were*
  read directly via `gh api` and are on firmer footing.
- **F3's underlying mechanism (why `GetFile(0)` reports USSEP for two records
  whose local IDs sit in the vanilla `Skyrim.esm` actor block) is not fully
  resolved** — this pass verified `TESForm::GetFile()`/`GetLocalFormID()`'s
  literal implementation and cross-checked the raw snapshot JSON, which together
  rule out "USSEP-native record" (contrast the guards' distinct ID range) but
  don't conclusively establish whether index-0-of-`sourceFiles` means "originating
  master" or something else for a record USSEP has patched. The load-order-
  dependent conclusion (keep USSEP active to match the table's verified state) is
  actionable either way, but a future session with load-order-toggling access
  (capture the same snapshot with USSEP removed and diff the result) could settle
  this properly instead of leaving it as an open mechanism question. This is also
  a candidate `docs/architecture.md` FormID-rule concern worth a maintainer's
  attention on its own: if `GetFile(0)`'s answer for a record really does depend
  on which overriding plugins are active, that's exactly the load-order-dependent
  identity instability the FormID rule was written to guard against, one layer
  up from the raw-FormID-persistence case the rule already covers.
- This report does not re-litigate the personal-playthrough Apostasy/Tuxborn/
  Mantella research already filed in `notes/skyrim-modlist-research/` — it reuses
  only the Proton/MO2 mechanics (Stock Game pattern, GE-Proton10-14, moshortcut
  launching) that generalize to any MO2 instance on this machine, not the modlist
  content choices themselves.
- Exact current Nexus mod IDs for powerofthree's Papyrus Extender (#22854) and
  PapyrusUtil SE (#13048) and USSEP (#266) are carried over from this project's own
  established references (`docs/architecture.md`'s SAL section, ADR-0008's pin
  table) rather than freshly re-verified against Nexus directly in this pass, for
  the same Cloudflare-403 reason noted above.

## Sources

- `docs/decisions/0008-game-version-pin.md`, `docs/research/11-version-pin-and-transport.md` — the existing 1.6.1170 pin, dependency table, and `download_depot` procedure
- `adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp` — direct read; source of F3's USSEP finding
- `docs/research/25-devbench-skse-mcp-verification.md` — DevBench verification this report builds on directly (F7)
- `docs/research/24-programmatic-esp-authoring.md` — house-style template for this report's structure
- `docs/architecture.md` (Deployment target, Game version pin sections) — same-machine Proton/Linux deployment fact underlying F7's correction
- `notes/skyrim-modlist-research/wabbajack-without-nexus-premium.md` — Stock Game pattern, `download_depot`/patcher landscape, Nexus Premium cost-benefit reasoning reused for F1/F2
- `notes/skyrim-modlist-research/ai-npc-dialogue-linux-compat.md` — SkyUI's ecosystem ubiquity cross-reference (F8)
- `tools/launch-ngvo-skse.sh` — GE-Proton10-14 version, `moshortcut://` launch mechanism, MO2-bottom-of-pane conflict-winning convention reused in the build-order section
- `notes/skyrim-ai-modlist-plan.md` — SkyrimNet's bottom-of-pane placement precedent, cited by analogy for ChronicleBridge's own placement
- <https://github.com/alandtse/CrashLoggerSSE/releases> (`gh api repos/alandtse/CrashLoggerSSE/releases` and `.../releases/tags/v1.25.0`) — v1.25.0 (2026-08-21, "support Skyrim AE 1.7.99") and v1.24.0 (2026-06-28) release/changelog data, fetched directly (F6)
- <https://www.nexusmods.com/skyrimspecialedition/mods/169962> (Best of Both Worlds downgrade patcher), <https://www.nexusmods.com/skyrimspecialedition/mods/188916> (SDT), <https://www.nexusmods.com/skyrimspecialedition/mods/188956> (Skyrim Downgrader) — page existence/titles/dates via web search, direct fetch blocked by Cloudflare 403 (F1)
- <https://www.nexusmods.com/skyrimspecialedition/mods/32444> (Address Library for SKSE Plugins), <https://www.nexusmods.com/skyrimspecialedition/mods/12604> (SkyUI), <https://www.nexusmods.com/skyrimspecialedition/mods/59818> (CrashLoggerSSE), <https://www.nexusmods.com/skyrimspecialedition/mods/181326> (DevBench) — page existence/description via web search, direct fetch blocked by Cloudflare 403 (F5, F6, F8)
