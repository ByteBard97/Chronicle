# SKSE_HTTP test harness — implementation plan (coordinator's answer)

**Re:** `notes/inbox/skse-http-test-harness-plan.md` (the planning request).
**Verdict up front:** build the two-piece probe, keep it entirely out of
the Chronicle repo, and treat it as a *de-risking spike* — its output is a
findings note, not code. This is **not** the start of the v0.2 seam: the
vision's "no in-engine code before the headless suite passes" exists to
stop the sim blocking on the seam, and this probe couples nothing to
anything. `adapters/skyrim/` stays empty until the real transport lane.

## Rulings on the four open questions

1. **Trigger → hotkey, not `OnInit()`.** You'll fire the probe dozens of
   times while debugging the listener; a once-per-load trigger makes
   every iteration a game restart. `RegisterForKey` in `OnInit`,
   `OnKeyDown` sends the request. Rebinding is a one-line change.
2. **ESP → one minimal ESP, built with the pinned Creation Kit** (the
   hash-mismatch fix from the 16:18 handoff holds). A loose `.pex` can't
   self-start — something must host the script, and a Start-Game-Enabled
   quest is the smallest host. Don't burn time hunting for an ESP-less
   path; if the CK fight exceeds ~1 hour, the fallback is building the
   quest record in SSEEdit instead (clone any tiny start-enabled quest,
   strip it, attach your script) — same artifact, different tool.
3. **Payload → hardcoded.** `{"probe": "hello-skyrim", "count": N}` with
   N incrementing per keypress — the counter makes duplicate/retried
   sends visible in the listener log. No game state, by design.
4. **Reverse direction → the reply path only, and yes, include it.** The
   listener returns a JSON body and the script's ModEvent handler reads
   it and `Debug.Notification()`s it. That's still game-initiates-request
   — the shipped API covers it, and it proves both directions of the
   socket in one shot. Server-*pushes*-to-game is out of scope (no such
   mechanism in SKSE_HTTP; that's a WebSocket-bridge conversation for the
   real seam, per ADR-0003).

## The two pieces

**Location:** everything throwaway lives in `~/skse-http-probe/` (source +
listener) and `~/Games/NGVO/mods/ZZChronicleProbe/` (the staged mod —
`ZZ` sorts it last in MO2 and marks it as ours; toggleable, deletable).
Nothing enters the Chronicle repo.

### Piece 1 — the listener (`~/skse-http-probe/listener.py`)

Python stdlib only, ~40 lines: `http.server.ThreadingHTTPServer` on
`127.0.0.1:8080`, a handler that on POST `/probe` reads the body, logs
timestamp + headers + body to stdout and `probe.log`, and replies
`200 {"reply": "pong", "received_count": <echo>}`. Run:
`python3 listener.py`. Sanity-check it yourself *before* touching the
game: `curl -X POST localhost:8080/probe -d '{"probe":"curl-test"}'`
should log and pong. This isolates "listener broken" from "game path
broken" up front.

### Piece 2 — the Papyrus caller (`ZZChronicleProbe`)

**First, one fetch:** the staged mod ships only `Scripts/SKSE_HTTP.pex` —
pull the API source `Source/Scripts/SKSE_HTTP.psc` from the GitHub repo
(`Leidtier/SKSE_HTTP`, tag v0.1.0-beta9) into
`~/skse-http-probe/includes/`. You need it twice: as a compile-time
include, and to **confirm the exact ModEvent names/signatures**
(`SKSE_HTTP_OnHttpReplyReceived` / `..._OnHttpErrorReceived` and what
the reply-dictionary handle is passed as) before writing the handler —
the planning request's API sketch is from that file, but read the real
signatures, don't compile against a summary.

**The script** (`ChronicleProbeQuest.psc`, one quest script):
- `OnInit()`: `RegisterForModEvent` for both reply/error events;
  `RegisterForKey(68)` (F10 — rebind if NGVO uses it; check first).
- `OnKeyDown()`: `createDictionary()` → `setString("probe",
  "hello-skyrim")` → `setInt("count", count)` → increment counter →
  `sendLocalhostHttpRequest(handle, 8080, "/probe")` →
  `Debug.Notification("probe sent #" + count)`.
- Reply event: `getString(handle, "reply", "<none>")` →
  `Debug.Notification("pong: " + reply)`. Error event: notification with
  the error string — visible failure without log digging.

**The ESP:** in CK, one plugin `ZZChronicleProbe.esp` (master:
`Skyrim.esm`), one quest `ChronicleProbeQuest`, Start Game Enabled,
script attached. Compile the `.psc` with `PapyrusCompiler.exe` (from the
pinned CK install) with `-i` covering vanilla `Scripts/Source`, SKSE's
sources, powerofthree's extender sources, and your
`~/skse-http-probe/includes/`; output into
`~/Games/NGVO/mods/ZZChronicleProbe/Scripts/`, ESP at the mod root,
`meta.ini` like SKSE_HTTP's staged folder. Enable in MO2, check it, done.

## Bring-up order (each step has its own yes/no)

1. `curl` the listener — proves piece 1 alone.
2. Launch the game; confirm `SKSE_HTTP.log` appears in the prefix SKSE
   dir (path in the 16:18 handoff) — proves the plugin loads at all.
   Missing → load-order/dependency problem, stop here and fix that first.
3. Main menu → load a save → press F10. **Success = three
   confirmations:** listener logs the POST with the JSON body (outbound
   through Proton networking — the one genuinely unverified link),
   "pong" notification in-game (reply path), `SKSE_HTTP.log` quiet.
4. Iterate freely on the listener (instant restart). Script changes need
   recompile + game restart — batch them.

**Triage map:** no listener log but "probe sent" shows → Proton
localhost issue (confirm with `ss -ltn | grep 8080`; try `127.0.0.1`
explicitly in the payload host if the API allows, else investigate the
prefix's hosts file). Error notification → connection refused (listener
down) or timeout (route/typo). Nothing at all on F10 → keybind conflict
or quest not running (check the ESP is enabled and the quest is
start-enabled).

## When it's green

Write the findings note to `notes/inbox/` (what worked, what the Proton
networking reality was, the confirmed ModEvent signatures, anything
surprising about the staged-mod workflow) and hand it to the Chronicle
planning agent. That note — plus ADR-0001/0003 — is the input to the
real `adapters/skyrim/` transport lane, which stays unscheduled until
the headless track says so. Delete or disable `ZZChronicleProbe` after;
it's scaffolding.

**Effort:** one evening, most of it CK/MO2 ceremony. The code in both
pieces together is under 100 lines.
