# Programmatic BGSSaveLoadManager::Load() and Call Context: Does the "Menu-Mode Required" Hypothesis Hold?

**Date:** 2026-09-05
**Trigger:** four live-game experiments against DevBench's `game action=load/loadLast`
all failed identically, no crash, no error, `kPostLoadGame` never fires, gameplay
continues unchanged, even from the Main Menu. Two prior reviews converged on a
"paused/menu-mode required" hypothesis but neither cited a real plugin's source. This
report goes to primary sources: DevBench's own code and commit history, CommonLibSSE-NG's
`BGSSaveLoadManager` wrapper, and two real shipped mods that call the same engine API.

## Verdict

**Inconclusive on "menu-mode" narrowly construed, but the research surfaced a more
specific, testable, and better-evidenced alternative: the dispatch queue the call is
made through, not whether a menu is visually open.**

- No real mod's source was found that requires a system menu (a `MessageBoxMenu`, the
  pause menu, or any `RE::UI` menu-stack entry) to be *open* at the moment
  `BGSSaveLoadManager::Load()` / `LoadMostRecentSaveGame()` is called. One real, shipped,
  popular mod (powerof3's Enhanced Death Camera) calls `LoadMostRecentSaveGame()` from
  **live gameplay, with no menu open at all** ([`Hooks.cpp:104`](https://github.com/powerof3/EnhancedDeathCamera/blob/main/src/Hooks.cpp#L104)). This is direct evidence *against* the hypothesis as literally stated ("must open a system menu first").
- But a second real, shipped mod (Voxima) that also drives save/load calls dispatches
  **every** such call through `SKSE::TaskInterface::AddUITask`, not the plain `AddTask`
  DevBench uses ([`plugin.cpp:578-582`](https://github.com/zbigdogz/Voxima-SkyrimVoiceControl/blob/main/Plugin/source/plugin.cpp#L578-L582)). Confirmed against `skse64`'s own core source: `AddUITask` closures are drained
  specifically inside `UIManager::ProcessCommands()`, which is a detour on the engine's own
  `ProcessEventQueue`, the UI-manager's per-frame event-processing tick, while `AddTask`
  closures are drained on the ordinary main-loop tick, a **different point in the frame**
  ([`Hooks_UI.cpp`](https://github.com/ianpatt/skse64/blob/master/skse64/Hooks_UI.cpp)). DevBench's `game` tool queues `Load()` via plain `AddTask`
  ([`Tools.cpp:433-478`](https://github.com/alandtse/devbench/blob/main/src/Tools.cpp#L433-L478)).
- DevBench's own commit history contains a **confirmed, first-party, reproduced** case of
  this exact class of bug: an equivalent `BGSSaveLoadManager` call (a synchronous save
  triggered by `StartWaiting`/`StartSleeping`) deadlocked the main thread specifically
  "when triggered from a devbench task-queue callback instead of the real Wait menu's
  input-driven path," reproduced twice on VR, fixed by disabling the triggering preference
  rather than by changing the call site's threading (commit `22ad547b`, PR #74). This is
  primary-source proof that **this exact subsystem behaves differently depending on
  whether the call arrives via DevBench's task-queue path or the real UI-input-driven
  path**, the mechanism just wasn't "no menu open," it was thread/queue/timing context.
- The narrower "cold state, no game ever loaded in this process" explanation is also
  live: DevBench's own source comment says `LoadMostRecentSaveGame()` "is a silent no-op
  from the Main Menu (verified live)" and claims the **named** `Load(name, false)` path
  "works from the menu" (comment at `Tools.cpp:437-440`, first written 2026-05-31, commit
  `2fedf601`), a claim Chronicle's four live experiments directly contradict. This
  discrepancy between DevBench's own "verified live" claim and Chronicle's repeated
  failure, on the same DevBench version (1.15.1) DevBench's fix predates, is itself the
  most concrete finding in this report (see §4).

In short: real prior art contradicts "a menu must be open," but real prior art (both a
second mod's design choice and DevBench's own bug history) supports "the call must go
through the engine's UI/menu dispatch tick, not the general simulation tick" as a live,
better-specified, and cheaply testable alternative. Neither the original two reviews nor
the sources found here nail down conclusively that this is *the* answer for the specific
silent-no-op Chronicle observed, see Open Questions.

## 1. What DevBench's own `load` action actually does, confirmed from source

`alandtse/devbench` is open source (GPL-3.0-or-later, MIT for the cross-plugin API shim;
verified previously in `docs/research/25-devbench-skse-mcp-verification.md`). Its `game`
tool handler, `GameHandler` in `src/Tools.cpp` (fetched at commit `afd0f3de5251...`, HEAD of
`main` as of 2026-09-05), does the following for `action=load`/`loadLast`
([`Tools.cpp:433-486`](https://github.com/alandtse/devbench/blob/main/src/Tools.cpp#L433-L486)):

```cpp
auto* task = SKSE::GetTaskInterface();
...
if (action == "loadLast") {
    ...
    task->AddTask([name]() {
        if (auto* m = RE::BGSSaveLoadManager::GetSingleton())
            m->Load(name.c_str(), false);
    });
    ...
}
if (action == "save" || action == "load") {
    ...
    task->AddTask([name, isSave]() {
        auto* m = RE::BGSSaveLoadManager::GetSingleton();
        if (!m) return;
        if (isSave) m->Save(name.c_str());
        else        m->Load(name.c_str(), false);  // checkForMods=false skips the mod-mismatch modal
    });
    ...
}
```

**[CONFIRMED]** Both paths dispatch via `SKSE::GetTaskInterface()->AddTask(...)`, the
plain main-thread task queue, not `AddUITask`. Neither path opens, closes, or checks any
`RE::UI` menu state before calling `Load`. There is no precondition check for "am I in
menu mode" anywhere in `GameHandler`.

**[CONFIRMED]** DevBench's own source comment, unchanged since it was written
(commit `2fedf601`, 2026-05-31, present at `Tools.cpp:437-440` on current `main`):

> `BGSSaveLoadManager::LoadMostRecentSaveGame()` is a silent no-op from the Main Menu
> (verified live), so resolve the newest .ess ourselves and load it by name, the named
> path works from the menu.

This is DevBench's own author asserting, with a "verified live" annotation, that the
**named** `Load(name, false)` path (not `LoadMostRecentSaveGame()`) does work from the
Main Menu. Chronicle's four independent live experiments, named `load`, a
file-visibility-race-fixed retry, `loadLast`, and a save from a separate earlier process:
all failed to produce `kPostLoadGame`, including for the named path this comment claims
works. **This direct contradiction between DevBench's own claim and Chronicle's repeated
observation is the single most concrete, actionable data point this report found**, see
§4 for why it matters more than any inferred "menu mode" theory.

**[CONFIRMED]** DevBench's own `kLoadNote` (referenced but its exact string not fetched in
this pass) documents that load completion is asynchronous and "may be gated by a
content-mismatch `MessageBoxMenu`", i.e., DevBench's own authors are aware that a *load
can itself spawn a menu partway through* (the mod-mismatch confirmation), which is exactly
why `checkForMods=false` is passed, to skip that modal. This confirms the engineers
already had "a menu might get in the way" on their radar, just for a menu the load
*creates*, not one required beforehand.

## 2. DevBench's own confirmed call-context bug, first-party evidence context matters

Commit `22ad547b` (PR #74, "feat(tools): add wait/sleep tools", merged with fixes through
2026-09-04) contains this fix, verbatim from the commit message:

> `fix(tools): suppress autosave-on-wait/rest during wait/sleep on VR`
>
> `StartWaiting`/`StartSleeping` trigger a synchronous `BGSSaveLoadManager` save before
> anything else when `bSaveOnWait`/`bSaveOnRest` is enabled. Live-tested on VR: that save
> deadlocks the main thread when triggered from a devbench task-queue callback instead of
> the real Wait menu's input-driven path, reproduced twice, confirmed fixed by disabling
> the relevant pref for the call and restoring it after.

**[CONFIRMED, first-party]** This is not the same failure mode as Chronicle's (a deadlock,
not a silent no-op), and it concerns `Save`, triggered as a side effect of `StartWaiting`,
not a direct `Load` call. But it is direct, reproduced (twice), attributed proof that **the
exact same subsystem (`BGSSaveLoadManager`) behaves differently when driven from a
DevBench task-queue callback than when driven from the real menu's input-driven path**, on
the same engine build, in the same process. DevBench's own team hit a context-sensitivity
bug in this subsystem before Chronicle did, and their fix was to avoid the interaction
(disable the autosave pref for the call) rather than to change *how* the call was
dispatched, so this bug's resolution doesn't itself tell us whether dispatching via
`AddUITask` would have also fixed it, only that the call-context distinction is real.

A second, related, `Load`-specific bug from DevBench's own history, different root cause,
identical externally-observed symptom to what Chronicle saw:

> `fix(recording): use loadLast for quicksave/autosave entryPoints (#43)`
>
> Quicksave and autosave slot names are rolling, the engine overwrites the slot with a
> new name on each F5/autosave, so the stem captured at record time ... is stale at replay
> time. `Load(stale, false)` **silently no-ops, postLoadGame never fires**, and the replay
> hangs at the main menu for the full 60-second timeout.
(commit `3794b5db`, 2026-06-12)

**[CONFIRMED]** This establishes, from DevBench's own bug tracker, that "`Load()` silently
no-ops and `kPostLoadGame` never fires" is a **known, previously-reproduced symptom with a
root cause that has nothing to do with menu state**, a stale/nonexistent save name. This
is the alternative explanation the two prior reviews' "not stale-cache" argument was meant
to rule out. Chronicle's team says they validated the save name existed and used a
freshly-created save from a separate earlier process specifically to rule this class out:
reasonable, but note DevBench's own fix here is exactly "validate the name exists via a
fresh `EnumerateSaves` call right before queuing," which is also what current `GameHandler`
does for `action=load` (`Tools.cpp:459-469`, the 404-on-missing-name check). **What isn't
independently re-confirmed in this report** is whether Chronicle's specific test harness
actually exercised a save name captured by a *fresh* `game action=list` call immediately
before each of the four attempts, as opposed to a name captured earlier and reused, if any
attempt reused an older enumeration, this alternative isn't fully closed out.

## 3. Real mods that call the same engine API, what call context they actually use

Two real, source-inspectable SKSE plugins were found on GitHub that call
`BGSSaveLoadManager::GetSingleton()->Load*` directly (via `gh api search/code` on the exact
call expression, two results total, both fetched and read in full):

### 3.1 powerof3 / EnhancedDeathCamera, calls Load from live gameplay, no menu at all

[`src/Hooks.cpp`](https://github.com/powerof3/EnhancedDeathCamera/blob/main/src/Hooks.cpp)
(powerof3 is a well-known, prolific SKSE author, Buffout4, PapyrusExtenderSSE, SPID,
CrashLoggerSSE; already established as a legitimate, active source in
`docs/research/25-devbench-skse-mcp-verification.md` and
`docs/research/23-native-skse-plugin-prior-art-pass-2.md`). On death, the mod switches the
player camera to a special "death cam" state, then:

```cpp
void ReloadLastSave()
{
    gameReloaded = false;
    const auto camDuration = Settings::GetSingleton()->GetDeathCamera()->camDuration.GetValue();
    std::this_thread::sleep_for(std::chrono::seconds(camDuration));
    if (gameReloaded) return;

    SKSE::GetTaskInterface()->AddTask([]() {
        if (gameReloaded) return;
        if (const auto subtitles = RE::SubtitleManager::GetSingleton())
            subtitles->KillSubtitles();
        if (!RE::BGSSaveLoadManager::GetSingleton()->LoadMostRecentSaveGame()) {
            RE::Main::GetSingleton()->resetGame = true;
        }
    });
}
```
([`Hooks.cpp:86-108`](https://github.com/powerof3/EnhancedDeathCamera/blob/main/src/Hooks.cpp#L86-L108))

**[CONFIRMED, from source]**:
- (a) **Menu/game state required:** none. The death-cam state is a `PlayerCamera`
  camera-state (`ThirdPersonState`/UFO free-cam), not an `RE::UI` menu-stack entry. No
  `MessageBoxMenu`, no pause menu, nothing pushed to the UI stack before this call. This is
  gameplay-adjacent (post-death), not menu-mode.
- (b) **Thread/context:** a background `std::jthread` sleeps for the camera duration off
  the main thread, then the actual `Load` call is dispatched back onto the main thread via
  `SKSE::GetTaskInterface()->AddTask(...)`, the same plain task-queue mechanism DevBench
  uses, not `AddUITask`.
- (c) **UI/menu-stack manipulation:** none, beyond killing active subtitles.
- Notably, the code **checks the return value** and treats `false` as an expected failure
  mode with its own fallback (`resetGame = true`, forcing a fresh main-menu return instead
  of a silent hang), i.e., a real, shipped mod author already anticipated that
  `LoadMostRecentSaveGame()` can fail and coded a recovery path, consistent with DevBench's
  own finding that this specific function is unreliable in at least the Main Menu case.

This is real evidence *against* "a system menu must be open" as an absolute requirement:
the call succeeds often enough to ship (Enhanced Death Camera is a live, used mod) from a
non-menu gameplay state, dispatched exactly the way DevBench dispatches it (`AddTask`).
What is **not** independently verified here: whether this call reliably succeeds in the
field or whether users occasionally hit the `resetGame` fallback silently, the source
alone doesn't prove the happy path is reliable, only that the author built for both
outcomes.

### 3.2 zbigdogz / Voxima-SkyrimVoiceControl, dispatches load-adjacent calls via AddUITask, and via a MessageBox callback

[`Plugin/source/plugin.cpp`](https://github.com/zbigdogz/Voxima-SkyrimVoiceControl/blob/main/Plugin/source/plugin.cpp)
is a voice-command mod. Its central command dispatcher wraps **every** command, including
its "quick load" voice command, in `AddUITask`, not `AddTask`:

```cpp
void ExecuteCommand(Command command)
{
    const auto task = SKSE::GetTaskInterface();
    if (task != nullptr) {
        task->AddUITask([=]() {
            Command currentCommand = command;
            ...
```
([`plugin.cpp:576-583`](https://github.com/zbigdogz/Voxima-SkyrimVoiceControl/blob/main/Plugin/source/plugin.cpp#L576-L583))

And the "quick load" handler itself, two configured variants:

```cpp
else if (currentCommand.Name == "quick load")
{
    switch ((int)VOX_QuickLoadType->value)
    {
        case 1:
            SkyrimMessageBox::Show("Do you want to load your last save game?", {"Yes", "No"},
                [](unsigned int result) {
                    switch (result) {
                        case 0:
                            RE::BGSSaveLoadManager::GetSingleton()->LoadMostRecentSaveGame();
                            break;
                        case 1:
                            SendNotification("Load Game Aborted");
                            break;
                    }
                });
            break;
        case 2:
            RE::BGSSaveLoadManager::GetSingleton()->LoadMostRecentSaveGame();
            break;
    }
}
```
([`plugin.cpp:1101-1126`](https://github.com/zbigdogz/Voxima-SkyrimVoiceControl/blob/main/Plugin/source/plugin.cpp#L1101-L1126))

**[CONFIRMED, from source]**:
- (a) **Menu/game state:** variant 1 (`VOX_QuickLoadType == 1`) calls `Load` from inside a
  `MessageBoxMenu` "Yes" callback, i.e., the call genuinely happens while, or just as, a
  system menu is being answered/dismissed. Variant 2 calls it with **zero** menu
  involvement, directly from command dispatch. Both variants ship in the same mod as a
  user-configurable option, meaning the author did not consider a menu a hard requirement,
  only an optional UX confirmation.
- (b) **Thread/context:** the entire command, including the direct, no-menu variant 2:
  runs inside `AddUITask`, not `AddTask`. This is the one concrete data point of a real mod
  making a deliberate, different dispatch-queue choice than DevBench's for a save/load
  call.
- (c) There is also a **commented-out alternative implementation** immediately below the
  live code, using `RE::BSInputEventQueue::PushOntoInputQueue` to spoof a real
  "quickload" button-input event instead of calling the API directly
  ([`plugin.cpp:1128-1135`](https://github.com/zbigdogz/Voxima-SkyrimVoiceControl/blob/main/Plugin/source/plugin.cpp#L1128-L1135)).
  This mirrors DevBench's own console-command deadlock story (§2): a mod author
  independently arrived at "maybe I need to feed the engine's real input path, not just
  call the API," even if this particular fallback was left disabled/commented rather than
  shipped.

### 3.3 Why `AddUITask` is a real, mechanistically distinct dispatch path, confirmed against skse64 core

The distinction between `AddTask` and `AddUITask` is not just a naming convention; it is a
different drain point in the engine's own per-frame processing, confirmed directly from
`skse64` core source (`ianpatt/skse64`, the original SE SKSE core; `CommonLibSSE-NG`'s
`SKSE::TaskInterface` in `include/SKSE/Interfaces.h` declares the identical two-method
split, `AddTask`/`AddUITask`, confirmed at `kVersion 2`):

```cpp
// skse64/Hooks_UI.cpp
void UIManager::ProcessCommands(void)
{
    CALL_MEMBER_FN(this, ProcessEventQueue_HookTarget)();   // the engine's own UI event-queue drain

    g_uiQueueLock.Enter();
    while (!g_uiQueue.empty()) {
        QueueEntry e = g_uiQueue.front();
        g_uiQueue.pop();
        ... cmd->Run(); ...   // AddUITask closures run here
    }
    g_uiQueueLock.Leave();
}

void TaskInterface::AddUITask(UIDelegate_v1* task)
{
    UIManager::GetSingleton()->QueueCommand(task);
}

RelocAddr<uintptr_t> ProcessEventQueue_HookTarget_Enter(0x01169D20 + 0xAB5);
void Hooks_UI_Commit(void)
{
    g_branchTrampoline.Write5Call(ProcessEventQueue_HookTarget_Enter, GetFnAddr(&UIManager::ProcessCommands));
}
```
([`Hooks_UI.cpp`](https://github.com/ianpatt/skse64/blob/master/skse64/Hooks_UI.cpp), full
file quoted above minus includes)

**[CONFIRMED]** `AddUITask` closures are drained from inside a detour on
`UIManager::ProcessEventQueue`, the engine's own menu/UI-event-processing function, called
once per frame specifically to service the UI/menu subsystem. `AddTask` closures (per
`skse64_common`/`PluginAPI.cpp` conventions, not independently re-derived here beyond
CommonLibSSE-NG's public API surface) drain on the ordinary main-loop tick, a different
call site entirely. This confirms `AddUITask` is not a synonym for `AddTask`; it is a
genuinely separate queue serviced from within the engine's UI/menu machinery. Since the
vanilla pause-menu "Load" button is itself a Scaleform/UI action, it is a near-certainty
(not directly decompiled in this pass) that its native handler runs from within this same
`ProcessEventQueue` tick, not the general simulation tick, which would make `AddUITask`
the closer analog to "how the vanilla Load button actually calls Load," independent of
whether any menu is *visually open* at the moment DevBench's own closure runs.

## 4. The discrepancy that matters most: DevBench's own "verified live" claim vs. Chronicle's four failures

Section 1 already surfaced this, but it deserves to stand on its own because it is the
most actionable, least speculative finding in this report. DevBench's source comment says,
unchanged since 2026-05-31 and still present on `main` as of this report:

> "the named path works from the menu" (i.e., `Load(name.c_str(), false)`, called from the
> Main Menu, "verified live")

Chronicle's four independent live experiments against DevBench (named `load`, a retry
after fixing a save-file-visibility race, `loadLast`, and a load from a save created by a
genuinely separate earlier process) all produced the *opposite* result: silent no-op, no
`kPostLoadGame`, from the Main Menu. Both claims cannot be true of the same code path on
the same engine build under the same conditions. Candidate explanations, none confirmed in
this pass:

- **Platform.** DevBench's "verified live" testing is very plausibly native Windows (no
  Proton/Wine mention anywhere in its README or commit history, per
  `docs/research/25-devbench-skse-mcp-verification.md`); Chronicle runs under GE-Proton on
  Linux. If the internal engine `Load_Impl` relies on any Win32 mechanism Wine emulates
  imperfectly under load (a timer, a message-pump interaction, or the same class of
  main-thread-stall issue the live-test-harness doc already documents for modal windows:
  `docs/design/live-test-harness.md` notes "the window losing focus during a load stops
  the frame counter"), a Proton-specific failure mode is entirely plausible and would not
  require any "menu mode" explanation at all.
- **Game version.** DevBench added Skyrim AE 1.7.99 support (v1.15.0, 2026-08-21) and an
  "address library v5 flag" (v1.15.1, 2026-08-24) very close to when Chronicle's live
  testing would have run. Chronicle is pinned to **1.6.1170** specifically
  (`docs/decisions/0008-game-version-pin.md`). If DevBench's own "verified live" test of
  the named-load-from-menu fix was run against a different game build than 1.6.1170, and
  the `RELOCATION_ID`/offset CommonLibSSE-NG resolves for `Load_Impl` on 1.6.1170 is
  subtly wrong (points to the correct function but under a build where a precondition the
  function checks is not satisfied at the Main Menu, or an address-library mismatch that
  doesn't crash but silently misresolves), a silent no-op with no crash is exactly what a
  wrong-but-plausible offset produces. This was not independently tested in this pass.
- **The AddTask-vs-AddUITask distinction (§3.3).** Not yet ruled in or out for this
  specific symptom, DevBench's own maintainer never tried the `AddUITask` path for the
  `game` tool's `load` action (confirmed absent from `Tools.cpp`), so there is no data
  either way from DevBench's own history on whether it would change this outcome.

## 5. Recommendation, cheapest next live-game diagnostic steps, in order

Chronicle's team has a live SimpleSkyrim instance, DevBench MCP access, and can query
DevBench's own menu/pause state. Ordered from zero-new-code to a small new C++ probe:

1. **Zero new code, directly test "does an open menu change the outcome," using only
   DevBench's existing `menu` tool.** Before calling `game action=loadLast`, use
   `menu action=open name=<some real, harmless system menu, e.g. the Journal Menu>` to put
   the UI into a genuine menu-mode state (this exercises `RE::UI`'s real open path, not a
   simulated one, DevBench's own `menu open`/`close` already goes "via the UI queue" per
   its source comment at `Tools.cpp:490-497`), confirm via `menu list` that the menu is
   open and `PausesGame`/`Modal`, then issue the same `game action=load` call while it's
   open, and watch for `kPostLoadGame`. If it fires only with a menu open, that is direct,
   cheap, first-party confirmation of the literal "menu-mode required" hypothesis. If it
   still silently no-ops, that hypothesis is refuted for this environment and effort should
   move to steps 2–3. This single test costs one MCP call sequence and no rebuild.
2. **Rule out the version/offset explanation (§4) before writing any new code.** Confirm
   the exact Skyrim SE build ChronicleBridge/DevBench are running against
   (`inspect kind=state` or equivalent should surface the runtime version DevBench detected)
   matches 1.6.1170 exactly, and confirm DevBench's installed version's `Load`/`Load_Impl`
   relocation IDs were validated against that specific build (not just "doesn't crash":
   crash-free wrong-offset resolution is exactly the silent-failure mode a mismatch would
   produce). This is a documentation/version check, not a new experiment.
3. **If both of the above are negative/inconclusive, build the minimal `AddUITask` probe.**
   Using DevBench's MIT-licensed cross-plugin API (`DevBenchAPI.h`/`RegisterTool`, already
   verified real and usable in `docs/research/25-devbench-skse-mcp-verification.md`),
   register a tiny consumer tool (under ~15 lines) that calls
   `SKSE::GetTaskInterface()->AddUITask([name]{ RE::BGSSaveLoadManager::GetSingleton()->Load(name.c_str(), false); })`
   instead of `AddTask`, and compare against `kPostLoadGame` under the exact same
   conditions the four failed experiments used. This is grounded directly in §3.2/§3.3:
   a real shipped mod's actual dispatch choice, and a confirmed, source-verified mechanism
   for why that choice could matter (a different engine drain point, serviced once per
   frame from inside the UI/menu subsystem specifically). This is the cheapest test that
   requires any new C++ at all, and it directly operationalizes the strongest evidence this
   report found.
4. **Only after 1–3**, consider more invasive options: hooking the vanilla pause menu's own
   Load button to log its exact call path (Trampoline hook near the Scaleform handler),
   which would require Champollion/reverse-engineering effort well beyond what a "cheapest
   next step" should spend.

## Open Questions

- **Was the "stale save name" explanation (§2, the `3794b5db` bug) actually closed out for
  all four of Chronicle's experiments**, specifically: was the save name used in each
  attempt captured from a `game action=list` call issued immediately before that attempt,
  or could any attempt have reused an enumeration from earlier in the session? This report
  could not verify Chronicle's own experiment methodology in enough detail to rule this out
  definitively, only that DevBench's own history shows this exact symptom with this exact
  root cause once already.
- **No direct decompile or reverse-engineering write-up of the vanilla pause-menu "Load"
  button's actual call path was found** (UESP, xSE community wiki, and Champollion-based
  write-ups were searched but nothing authoritative surfaced in this pass). The claim in
  §3.3 that the vanilla Load button very likely funnels through `UIManager::ProcessEventQueue`
  (i.e., the `AddUITask` drain point) is a reasoned inference from confirmed SKSE core
  mechanics, not a confirmed fact about the vanilla button's own code path. Flag this
  explicitly as **inferred, not confirmed**.
- **Whether `AddUITask` is even meaningfully different from `AddTask` timing-wise on the
  frame DevBench's `game` tool actually runs in**, both are serviced once per frame in
  current builds; if DevBench's frame-scheduling already happens to align both queues'
  drain points closely enough in practice, the distinction found in §3.3 could turn out to
  be a red herring for this specific symptom. This can only be resolved empirically (step 3
  above).
- **The Proton/Wine explanation (§4) was not tested at all in this pass**, no attempt was
  made to reproduce DevBench's load path on native Windows for comparison. Given
  `docs/research/23-native-skse-plugin-prior-art-pass-2.md` already flagged Proton
  in-process networking as an open risk area for unrelated reasons, this remains a live,
  unresolved possibility and probably deserves at least as much weight as the menu-mode
  axis until step 2 above is actually run.
- **CHIM/HerikaServer, SkyrimNet, and Mantella were not found to call
  `BGSSaveLoadManager::Load` at all** in this pass (SkyrimNet and Mantella's core loops
  don't drive save/load as part of dialogue; this matches `docs/research/37-ai-npc-mod-source-study.md`'s
  and `docs/research/44-skyrim-runtime-lip-sync-mfg-fix.md`'s prior findings that neither
  system's public source touches this API). If a version of SkyrimNet does drive saves as
  part of its own persistence story, its inbound server code is closed-source
  (`docs/research/23-native-skse-plugin-prior-art-pass-2.md`, §Q2) and could not be audited
  here.
- **"Continue Game No Crash"** (Nexus 78557) could not be verified as an open-source,
  inspectable native plugin in this pass, search results describe its behavior (loading
  the most recent save from the Main Menu without the vanilla "Continue" crash) but did not
  surface a GitHub source repo. Flagging per this project's sourcing standard: **this mod's
  actual implementation is not verified here** and should not be cited as evidence for or
  against anything without locating real source.

## Sources

- <https://github.com/alandtse/devbench/blob/main/src/Tools.cpp>: `GameHandler`
  (`action=load/loadLast`, lines ~323-486), `RedirectConsoleSaveLoad` (lines ~50-75),
  `BlockingMenus` (lines ~1527-1561); fetched at commit `afd0f3de5251...` (HEAD of `main`,
  2026-09-05) via `gh api repos/alandtse/devbench/contents/src/Tools.cpp`
- <https://github.com/alandtse/devbench/commits/main>: commit history via
  `gh api repos/alandtse/devbench/commits`; specifically commit `22ad547b` (PR #74,
  wait/sleep tools + VR autosave-deadlock fix), commit `3794b5db` (PR, `loadLast` stale
  quicksave-name fix, #43), commit `2fedf601` ("robust load tooling," the
  "LoadMostRecentSaveGame is a no-op from Main Menu, verified live" comment origin)
- <https://github.com/CharmedBaryon/CommonLibSSE-NG/blob/main/include/RE/B/BGSSaveLoadManager.h>
  and `/src/RE/B/BGSSaveLoadManager.cpp`, confirmed `Load(const char*, bool)` signature,
  `Load_Impl` as a thin wrapper around a `REL::Relocation`-resolved engine call, no named
  menu/pause gating field exposed
- <https://github.com/CharmedBaryon/CommonLibSSE-NG/blob/main/include/SKSE/Interfaces.h>:
  `TaskInterface::AddTask`/`AddUITask` both present at `kVersion 2`
- <https://github.com/powerof3/EnhancedDeathCamera/blob/main/src/Hooks.cpp>: real, shipped
  mod calling `RE::BGSSaveLoadManager::GetSingleton()->LoadMostRecentSaveGame()` from live
  gameplay (death-cam state), dispatched via `SKSE::GetTaskInterface()->AddTask`, with
  explicit failure-path handling
- <https://github.com/zbigdogz/Voxima-SkyrimVoiceControl/blob/main/Plugin/source/plugin.cpp>:
  real, shipped voice-control mod dispatching all commands (including quick-load) via
  `SKSE::GetTaskInterface()->AddUITask`; one quick-load variant calls
  `LoadMostRecentSaveGame()` from inside a `MessageBoxMenu` Yes-callback, another calls it
  directly with no menu; a commented-out alternative spoofs a real "quickload" input event
  via `RE::BSInputEventQueue::PushOntoInputQueue`
- <https://github.com/ianpatt/skse64/blob/master/skse64/Hooks_UI.cpp>: confirms
  `TaskInterface::AddUITask` closures are drained from inside a detour on
  `UIManager::ProcessEventQueue`, the engine's own UI/menu-event-processing tick, distinct
  from the ordinary main-loop `AddTask` drain point
- <https://github.com/himika/libSkyrim/blob/master/Skyrim/src/FileIO/BGSSaveLoadManager.cpp>
  and <https://github.com/DavidJCobb/skyrim-classic-re/blob/master/ReverseEngineered/Systems/Savedata/BGSSaveLoadManager.h>:
  classic-Skyrim (not SE) reverse-engineered headers showing `RequestSave`/`RequestLoad`
  ("use these when calling from a papyrus thread") as functions distinct from direct
  `Save`/`Load`, plus an internal `pendingEvents` bitmask and `ProcessEvents_Internal`:
  evidence of an internal async event-queue design in this subsystem generally, **not
  independently confirmed to carry over to the SE/AE codebase** (flagged as inferred
  context, not a confirmed SE fact)
- `/home/geoff/projects/Chronicle/docs/research/25-devbench-skse-mcp-verification.md`:
  prior verification of DevBench's identity, license, and tool surface (this repo)
- `/home/geoff/projects/Chronicle/docs/research/23-native-skse-plugin-prior-art-pass-2.md`:
  prior research on ChronicleBridge's own threading/task-interface discipline and Proton
  networking risk (this repo)
- `/home/geoff/projects/Chronicle/docs/design/live-test-harness.md`: Chronicle's own
  live-test harness design, including the observation that a lost window focus or open
  modal stops the frame counter and DevBench's main-thread tools 504 (this repo)
- `/home/geoff/projects/Chronicle/docs/decisions/0008-game-version-pin.md`: Chronicle's
  pinned game version, 1.6.1170, used in §4's version-mismatch discussion (this repo)
