# Planning request: minimal SKSE_HTTP test harness

## Goal

Before wiring up Chronicle's real `adapters/skyrim/` transport (the seam
described in `adapters/skyrim/README.md`, architected per
`docs/decisions/0001-external-service-architecture.md` and
`docs/decisions/0003-substrate-choice.md`), we want the smallest possible
end-to-end test that proves the game can talk to a local process at all.
Deliberately not building the real thing yet — too many moving parts to
debug at once. Just: can the game send something, and can we receive it.

## What SKSE_HTTP actually is (read this before planning — it inverts the
obvious assumption)

SKSE_HTTP (`https://github.com/Leidtier/SKSE_HTTP`, MIT, v0.1.0-beta9,
2025-01-09) is **not** a server the game hosts for us to query. It makes
**the game itself act as an HTTP client**, sending a request out to a
server that we run locally. This is the same pattern Mantella uses
(game POSTs to `Mantella.exe` on port 4999).

Its Papyrus API (from `Source/Scripts/SKSE_HTTP.psc`, the only piece that
matters for this test):

```papyrus
function sendLocalhostHttpRequest(int typedDictionaryHandle, int port, string route, int timeout = 0) global native
function raiseOnHttpReplyReceived(int typedDictionaryHandle) global   ; fires ModEvent "SKSE_HTTP_OnHttpReplyReceived"
function raiseOnHttpErrorReceived(int typedDictionaryHandle) global   ; fires ModEvent "SKSE_HTTP_OnHttpErrorReceived"

; Dictionary helpers used to build the request payload / read the response:
Int function createDictionary() global native
String function getString(Int object, String key, String default="") global native
Bool function setString(Int object, String key, String value) global native
; ... getInt/getFloat/getBool/getIntArray/etc. mirror this pattern
```

There is **no bundled README or example caller** — the mod ships only the
DLL + this API script. Nothing calls `sendLocalhostHttpRequest` out of the
box.

## Current state (as of 2026-08-23)

- NGVO (the Skyrim modlist) is installed, boots to the main menu, confirmed
  working.
- `SKSE_HTTP` is staged as a manually-installed MO2 mod (not through MO2's
  installer — files extracted directly), checked/active in the load order.
  Its two dependencies, `Address Library for SKSE Plugins` and
  `powerofthree's Papyrus Extender`, are confirmed present and active.
- User just clicked **Run** in MO2 (launching via SKSE) for the first time
  with SKSE_HTTP active. Not yet confirmed whether it loaded cleanly —
  check for a new `SKSE_HTTP.log` in
  `.../compatdata/4190904829/pfx/drive_c/users/steamuser/Documents/My Games/Skyrim Special Edition/SKSE/`
  or an error in `skse64_loader.log` if that log is missing.
- No code exists yet in `adapters/skyrim/` (Chronicle's Python-side seam) —
  this test harness would be the first thing to touch that directory, or
  could live entirely outside it as a throwaway script if that's cleaner.
- Game runs under Proton on Linux (Steam App ID `4190904829` for the NGVO
  shortcut), not native Windows — anything involving paths, `localhost`
  networking, or process launching should account for that (Proton's
  network stack passes through to the host normally, so a plain
  `localhost:<port>` Python server on the Linux side should be reachable
  from the Proton-side game process without extra config, but this hasn't
  been verified in practice yet).

## What "minimal test" should probably mean

Two pieces, deliberately as small as possible:

1. A local HTTP listener (any stack is fine — Python's stdlib `http.server`
   is probably enough) that logs whatever the game sends and returns a
   trivial fixed response.
2. A minimal Papyrus script/mod that calls `sendLocalhostHttpRequest` under
   some easy-to-trigger condition (a hotkey via SKSE's input-event
   handling, or simplest of all, on game load / `OnInit()` of a quest
   script) and does something observably visible in-game with the reply
   (e.g. `Debug.Notification()` of the response body) so success/failure is
   obvious without digging through logs.

Open questions for the planning agent to resolve, not answered here on
purpose:

- Best trigger mechanism for the test call (hotkey vs. on-load vs. console
  command via `ConsoleUtil` if that's available) — pick whichever is
  fastest to get working and easiest to re-trigger repeatedly while
  iterating.
- Whether the Papyrus script needs a Creation Kit-built ESP to attach to,
  or can be a pure loose script + `.pex` compiled independently (Creation
  Kit for NGVO's exact build is already installed and pinned — see the
  handoff below if the compiler toolchain needs revisiting).
- What data to actually send in the test payload — doesn't need to be
  meaningful game state yet, a hardcoded string/counter is fine for this
  pass. Real event data (deaths, crimes, dialogue, etc.) is explicitly
  out of scope here.
- Whether to test the reverse direction (Python -> game) at all in this
  pass, or defer that entirely — SKSE_HTTP's shipped API only covers
  game-initiates-request; anything else would need a different mechanism
  and is probably out of scope for "smallest possible test."

## Relevant background docs (read as needed, not required for the plan
itself)

- `docs/decisions/0001-external-service-architecture.md`
- `docs/decisions/0003-substrate-choice.md` (amended 2026-08-20 — standalone
  bridge is primary, SkyrimNet is optional/secondary)
- `docs/research/01-skyrim-modding-substrate.md`,
  `docs/research/11-version-pin-and-transport.md` (SKSE_HTTP / transport
  survey)
- `adapters/skyrim/README.md` (the seam this eventually feeds into)
- `HANDOFF-2026-08-23-1618.md` (most recent handoff, full session context)

## Ask

Produce a concrete, minimal implementation plan for the two-piece test
harness above: what files to create, where (inside `adapters/skyrim/` or a
throwaway scratch location — your call), the exact Papyrus script contents,
the exact Python listener contents, and the steps to compile/package/load
the Papyrus mod into NGVO's MO2 install and trigger it. Optimize for fewest
moving parts and fastest iteration loop, not for anything resembling
production code.
