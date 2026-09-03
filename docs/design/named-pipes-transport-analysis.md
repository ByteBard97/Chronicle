---
date: 2026-08-27
status: draft
topic: "Real cost/benefit analysis of swapping ChronicleBridge<->listener transport from HTTP to named pipes"
supersedes-in-part: "docs/design/architecture-delta-audit.md's Named Pipes IPC row (that pass classified the idea abstractly; this one prices it)"
---

# Named pipes vs. HTTP for the ChronicleBridge <-> listener transport

## Recommendation, up front

**Do not switch. Not "parked, revisit later" — actively wrong for this
project's real deployment, independent of migration cost.** The decisive
fact isn't the code-churn estimate below (real, but survivable); it's that
this codebase's own files document two live deployment topologies where the
game and the Python service are **not on the same OS instance**, and named
pipes cannot cross either boundary without extra machinery that would cost
more than the HTTP transport it replaces:

1. **Cross-machine over LAN** — `OutboundClient.h`'s `OutboundConfig::host`
   comment says outright: *"the Chronicle host's LAN IP once running on a
   separate machine"*, and `listener.py`'s module docstring says the
   listener binds `0.0.0.0` *"because the real topology is a separate
   Windows machine on the LAN POSTing in — it can't be restricted to
   loopback."* This isn't hypothetical scaffolding: `docs/research/25-
   devbench-skse-mcp-verification.md` documents an actual second Windows
   box on this project's LAN (`192.168.0.211`) reached today via SSH port
   tunneling for a different loopback-bound tool (DevBench). The same
   pattern is the documented fallback for ChronicleBridge/listener too, per
   `chronicle-bridge-verification-runbook.md`'s "if game and listener aren't
   on the same machine" instruction.
2. **Cross-OS-boundary on one physical machine (today's actual dev setup)**
   — `tools/launch-chronicledev-skse.sh` runs the game as a Windows binary
   under GE-Proton (Wine), while `listener.py` runs as a native Linux
   process on the same host. HTTP works here because Wine forwards Winsock
   calls straight to the Linux kernel's real TCP/IP stack — a loopback
   socket opened by Wine-hosted code and one opened by native Linux code
   are the same kernel object. Win32 named pipes have no equivalent: they
   are implemented by `wineserver`, Wine's own userspace IPC broker, and
   are not exposed to the host OS as any filesystem object, socket, or
   named object a native Linux process could open. A native Linux Python
   process cannot `ConnectNamedPipe` into a Wine process's pipe namespace
   at all, today, with no workaround short of running the listener under
   Wine too (see the Windows/Proton section below).

TCP sockets already have exactly the boundary-crossing property this
project needs — same-machine loopback and cross-machine-over-LAN are the
*same code path*, differing only in the `host` config value, and the LAN
case already has a working, tested tunneling fallback (SSH -L) precedented
elsewhere in this repo. Named pipes have neither property. Swapping to them
would need to keep an HTTP (or equivalent socket) fallback for the
cross-machine case anyway, which means shipping and maintaining *two*
transports instead of one — pure cost, no removed complexity.

If a concrete future requirement narrows the deployment to "game and
listener always on the same real Windows machine, never Proton, never
LAN-split," most of this analysis's blocking objection goes away and named
pipes become a defensible (if still not obviously *better*) choice — see
"When this recommendation would flip," at the end.

---

## 1. What named pipes would actually look like here

### 1a. The cross-boundary question, answered as far as it can be without a live test

Windows named pipes (`\\.\pipe\name`) are a **kernel-level object on a
Windows NT kernel**. Two consumers can be full Win32 processes on the same
machine, or full Win32 processes on different machines talking over SMB
(`\\othermachine\pipe\name`) — but in both cases, *every* endpoint is a
Windows process going through the real Win32 API (`CreateNamedPipe`/
`CreateFile`), backed by either the local NT kernel or the SMB named-pipe
transport (`\PIPE\` over port 445).

Under Wine/Proton, `CreateNamedPipe`/`ConnectNamedPipe`/`ReadFile`/
`WriteFile` are implemented by Wine's own reimplementation, brokered
through `wineserver` (a single Linux process per Wine prefix that emulates
NT kernel objects — handles, pipes, mutexes, etc. — in userspace). This
emulation is **internal to that Wine prefix's process tree**. There is no
mechanism by which a plain native Linux process (the Python listener, run
directly by `uv run ... listener.py`, never through Proton) can see or open
a pipe object living inside `wineserver`'s namespace — Wine does not expose
its NT namespace as Linux filesystem paths, abstract sockets, or anything
else a non-Wine process could target. This is a structural property of how
Wine implements NT objects, not a configuration gap.

**What I could not verify empirically** (would need a live Proton+game
session to confirm, which this task's constraints and "do not touch
`~/Games/ChronicleDev`" rule out): whether Wine ships any documented
escape hatch (e.g., a "winepipe helper," a `wineserver`-side socket that
proxies named-pipe I/O to the host) that some other project uses for this
exact cross-boundary case. I did not find one in this repo's own prior
research (`docs/research/23-native-skse-plugin-prior-art-pass-2.md`, the
version-pin/transport survey) and none of the three AI-NPC framework
precedents this project already studied (Mantella, CHIM, SkyrimNet) use
named pipes — Mantella and CHIM both use HTTP-family transports precisely
because they face this same "the game is a Windows process, the AI backend
often isn't" problem. That absence is itself informative: if a
well-trodden Wine-side named-pipe bridge existed, one of these three
mature, actively maintained projects had the same incentive to use it and
apparently didn't.

The only way to run named pipes end-to-end here without inventing new
plumbing is to **run the Python listener itself inside the same Wine
prefix**, as a Windows Python interpreter under Proton, talking to
`\\.\pipe\ChronicleBridge` the normal Win32 way. That is a real option but
a much bigger change than "swap the transport" — it drags the entire
Python service (or at minimum a thin relay component within it) into the
Wine/Windows-Python dependency surface, something ADR-0001 explicitly
chose to avoid ("Chronicle runs as an external Python service... The
simulation itself never runs inside the game process" — a Wine-hosted relay
process isn't literally inside the game process, but it inherits Wine's
packaging/dependency fragility that ADR-0001's stated rationale was trying
to sidestep).

### 1b. Concrete code change, if pursued anyway (same-machine-only, real Windows, no Proton)

Assuming the blocking issue above is waived (single real Windows box,
game and listener co-located, no LAN split — see "when this recommendation
would flip"):

**C++ side (`OutboundClient.h`/`.cpp`, 295 + 739 = 1,034 lines today):**
- Every one of the 9 public functions (`PostPositionSnapshot`,
  `PostGameEvent`, `FetchHydrationPairs`/`PostHydrationAck`,
  `FetchAvoidancePairs`/`PostAvoidanceAck`, `FetchVendorMarkupPairs`,
  `FetchEvidenceEntries`/`PostEvidenceAck`) currently constructs an
  `httplib::Client`, sets three timeouts, and calls `.Get`/`.Post`. Every
  one would be rewritten to open (or reuse) a pipe handle via `CreateFile`/
  `WaitNamedPipe`, then `WriteFile` a framed message and `ReadFile` a
  framed response. That's a full rewrite of roughly 400-500 of this file's
  739 lines (every function body, not just the transport calls — HTTP
  status codes disappear as a concept, so the many `result->status ==
  503` / `< 200 || >= 300` branches need an equivalent success/failure
  signal invented from scratch).
- `cpp-httplib` (a single-header dependency, already vendored) gets
  dropped; nothing replaces it for free — Win32 pipe I/O is raw handles,
  no framing, no keep-alive, no per-request headers. A bearer-token
  equivalent to `X-Chronicle-Bridge-Token` has to be reinvented as part of
  the new message envelope (today it's an HTTP header; a pipe has no
  header concept).
- The 9 JSON build/parse helper functions in the anonymous namespace
  (`BuildPositionSnapshotJson`, `ParseHydrationPairsJson`, etc. — roughly
  350 of the file's 739 lines) are transport-agnostic and would survive
  untouched; only the code that puts bytes on the wire and reads them back
  changes. This is the one piece of the migration that's genuinely cheap.
- New concern with no HTTP equivalent: **connection lifecycle.** HTTP's
  request/response model means `httplib::Client` is stateless per call —
  today's code opens a fresh client on every single poll, at 8-second
  intervals, and that's fine. A named pipe is a stateful handle: does
  ChronicleBridge hold one open pipe handle per logical channel for the
  plugin's lifetime (9 open handles across 5 pollers, needing lifecycle
  management, reconnect-on-listener-restart logic, and correct handling of
  `ERROR_PIPE_BUSY`/`ERROR_BROKEN_PIPE`), or reopen a pipe on every poll
  (defeats a chunk of the latency benefit named pipes are chosen for, and
  still needs the same reconnect logic for the "listener isn't running
  yet" case HTTP already handles for free via connection-refused)? This is
  new design work, not just new code — HTTP's request/response framing
  hides an entire connection-management problem that a raw pipe exposes.

**Python side (`listener.py`, 1,387 lines today):**
- `BaseHTTPRequestHandler`/`ThreadingHTTPServer` (stdlib `http.server`)
  gives method routing (`do_GET`/`do_POST`), path dispatch (the
  `if self.path == "/whiterun/..."` chains), status codes, and
  `Content-Length`-based body framing entirely for free. None of that
  exists for named pipes: `multiprocessing.connection.Listener` (the
  Python stdlib's closest analog, using `family='AF_PIPE'` on Windows)
  gives you a byte-stream duplex channel and nothing else — no routing, no
  method verbs, no status codes. A hand-built protocol distinguishing "GET
  hydration" from "POST hydration/ack" from "POST positions" etc. across
  9 routes has to be designed and implemented: minimally, an
  operation-name-plus-length-prefixed-payload framing, re-dispatched
  through the same 9 `_handle_*` functions this file already has (those
  functions' *bodies* — the state-machine logic in `_hydration_pairs`,
  `_apply_hydration_ack`, etc. — are transport-agnostic and survive
  untouched, same as the C++ JSON builders).
- Realistic estimate: 150-250 new/changed lines for the pipe listener loop
  plus a hand-rolled routing layer, replacing roughly 100 lines of
  `do_GET`/`do_POST`/`_read_body`/`_check_auth` plumbing that
  `BaseHTTPRequestHandler` currently makes close to free. Net: more code,
  not less, because HTTP's routing/framing/status-code vocabulary is
  being reimplemented by hand rather than removed.
- `multiprocessing.connection` on the *server* side also only supports
  one connected client per `Listener.accept()` at a time by default in
  the simplest usage pattern — the current `ThreadingHTTPServer` handles
  N concurrent short-lived connections (today: up to 5 concurrent pollers)
  trivially. Supporting 5 concurrent long-lived pipe clients needs either
  5 separate named pipe instances (`CreateNamedPipe`'s own multi-instance
  support, `PIPE_UNLIMITED_INSTANCES`) or a manual accept-loop-per-instance
  pattern — again, new design surface HTTP's stdlib server already closed.
- Auth: `secrets.compare_digest(token, shared_secret)` against an HTTP
  header has no pipe equivalent; Windows named pipes have their own ACL
  model (`SECURITY_ATTRIBUTES` on `CreateNamedPipe`) which is a
  legitimately *stronger* mechanism in the same-machine case (OS-level
  access control instead of a bearer token) — but it only applies in the
  same-machine, no-Proton scenario this whole analysis is conditioned on;
  it does nothing for the LAN case, where the current shared-secret model
  is what's actually carrying the weight today.

**Rough total estimate**: 4-6 files touched
(`OutboundClient.h/.cpp`, `listener.py`, plus every one of the 5 poller
`.cpp` files' error-handling branches that inspect the old HTTP-status
convention), on the order of 600-900 lines net changed/added across C++
and Python combined — smaller than "rewrite everything" but not a small
patch, and concentrated entirely in glue/protocol code with no reduction
in the actual business logic (state machines, JSON shape, poll cadence)
that HTTP was never coupled to in the first place.

**Test suite (`test_listener.py`, 1,295 lines, 75 tests):** every test
that drives the listener via `http.client.HTTPConnection` (confirmed at
the top of that file — this is a real, non-mocked transport-level
integration test, not a unit test with a stubbed transport) needs its
setup/connection code rewritten for whatever pipe-connection object
replaces it. The assertions themselves (state-machine outcomes, JSON
shapes) mostly survive, but the harness — `ThreadingHTTPServer` startup/
teardown, `conn.request(...)`, `conn.getresponse()` — is transport-coupled
throughout and would need a parallel pipe-based harness. This is real,
non-trivial rework, not a find-and-replace.

---

## 2. What's the actual, measured problem with HTTP today?

**None found.** I searched this project's own history — every `HANDOFF-
*.md` file, every commit message via `git log --oneline --all | grep -i
http\|listener\|transport`, and every `docs/research/` file — for any
recorded latency spike, dropped-connection incident, firewall/loopback
friction, or performance complaint tied to the HTTP transport specifically.
The only two commits referencing this transport are a research pass
confirming the SSH-tunnel workaround for a *different* tool's loopback
binding (DevBench, not ChronicleBridge/listener) and the prior
"architecture delta audit" that raised named pipes as a hypothetical.
`architecture-delta-audit.md`'s own words on this exact point:
*"no concrete problem with HTTP has been identified yet (latency budget
was 0001's own named risk, and nothing since has shown it's binding)"* —
that finding holds up under this deeper pass; nothing new surfaced it.

**Doing the actual math on this project's real cadence, not a generic
IPC benchmark:**

| Channel | Cadence | Payload size (real, from code) | Requests/sec |
|---|---|---|---|
| Position snapshot (`PostPositionSnapshot`) | 1 Hz (`plugin.cpp:75`) | `wall_ts` + N × `{id,name,x,y}` — the file's own comment: "hundreds of NPCs at ~40 bytes/entry... well under 100KB." Whiterun's actual named-cast is 19 NPCs (`NAMED_CAST_NPC_IDS`); even generously counting every generic actor in the cell, this is single-digit KB. | 1.0 |
| Hydration poll+ack | 8s (`HydrationPoller.cpp`) | A JSON array of changed pairs only (dedup'd — usually 0-2 entries at ~60 bytes each) | 0.125 (poll) + occasional ack |
| Avoidance poll+ack | 8s | Same shape, smaller (bool not int) | 0.125 |
| Vendor-markup poll | 8s (no ack) | Same shape | 0.125 |
| Evidence poll+ack | 8s | Same shape, one-shot | 0.125 |

Steady-state total: **~1.5 requests/second**, worst-case payload a few KB,
typical payload well under 1KB. This is not a hot loop by any definition —
it's roughly two orders of magnitude below the request rate (thousands/sec)
where HTTP-over-loopback's per-request overhead (socket syscalls, header
parsing, TCP slow-start avoided via `Connection: keep-alive` but each of
these calls opens a *fresh* `httplib::Client`, so it isn't even using
keep-alive today) becomes a measurable fraction of a latency budget.

**Loopback HTTP overhead, quantified**: a fresh TCP connection + HTTP
request/response round-trip on loopback is typically low-single-digit
milliseconds (socket setup, header parse, no real network transit — the
handshake is local, not routed). At 1.5 req/sec, that's under 0.5% duty
cycle even at a pessimistic 3ms/request. Every poller already carries a
1-second `connection_timeout`/`write_timeout`/`read_timeout`
(`OutboundClient.cpp`, every `Fetch*`/`Post*` function) specifically
because these calls are fire-and-forget, non-blocking-of-gameplay, and
tolerant of an occasional miss — the code's own design already assumes
"this can be slow or fail sometimes, and that's fine," which is the
opposite of a system under real latency pressure. There is no gameplay
path (dialogue-tier response time, frame time) that this transport sits
on; the tightest cadence in the whole system is 1 Hz, three orders of
magnitude looser than a per-frame budget.

**Conclusion for this section**: the case for named pipes here is not
"HTTP is measurably too slow" (no evidence supports that) but "named pipes
are a more idiomatic Windows-native IPC primitive" — a real but purely
aesthetic/architectural preference, not a performance argument this
project's own numbers support.

---

## 3. Migration cost vs. benefit, side by side

| | HTTP (today) | Named pipes |
|---|---|---|
| Code to touch | 0 (already built, working, tested) | ~600-900 lines across `OutboundClient.h/.cpp`, `listener.py`, 5 poller files' error paths |
| Framing/routing | Free (`http.server` + `httplib`) | Hand-rolled, ~150-250 new Python lines, new C++ envelope design |
| Cross-machine (LAN) support | Native — same code path as loopback, just a different `host` value; SSH-tunnel fallback already precedented in this repo for the loopback-bound-service case | Not supported without SMB (both ends must be Windows, no Linux listener) or reinventing a tunnel-equivalent for named pipes (exotic, not precedented anywhere in this project) |
| Cross-Proton-boundary support (today's actual dev setup) | Works today, in production, right now | Does not work without running the listener under Wine too — a materially bigger change than "swap the transport" |
| Auth model | Bearer-token header, explicitly "not real security, stops opportunistic LAN neighbors" (listener.py's own words) | OS ACL (same-machine only) or reinvented token-in-envelope (cross-machine) |
| Test suite impact | N/A | 75 tests' transport-level harness (`test_listener.py`) needs a parallel implementation; assertions mostly survive, scaffolding does not |
| ADR-0005 handshake (HELLO/RESOLVE/ACK) | Not yet built against either transport — ADR-0005 explicitly defers the transport choice, describes the protocol in message-type terms (`SYNC_TIMELINE`, `TIMELINE_READY`, `MUTATION_EVENT`) that are transport-agnostic on paper | Same message types would need re-verification against a stateful-connection model instead of HTTP's request/response one — the "never-block" DEGRADED-mode design (buffer-and-reconcile on reconnect) assumes a model where "the service is unreachable" is a clean, immediate, per-call failure (HTTP: connection refused); a pipe's `ERROR_PIPE_BUSY`/broken-pipe-mid-write failure modes are a different shape of "unreachable" that this ADR's design doesn't yet address either way — not disqualifying, but unexamined, added risk on top of the ADR-0005 rework this ADR itself already flags as unresolved-either-way |
| Measured benefit today | — | **None found** (Section 2) |

The migration is not free even under the most favorable framing (real
Windows, no Proton, no LAN split) — 600-900 lines of glue-code rewrite,
full test-harness rework, and new unexamined failure-mode design work in
exactly the area (ADR-0005's save/reload race-fencing) this project has
already invested the most care in getting right. Weighed against a
benefit column that is empirically empty, this doesn't clear a "worth
doing" bar even before Section 1's structural blocker.

---

## 4. Middle paths

**Keep HTTP for everything; this is already the middle path.** The
"debug tooling wants to curl it" argument for keeping HTTP doesn't even
need to be invoked here — HTTP already wins on every axis this project's
own topology cares about (LAN, Proton-boundary, existing tooling) without
giving up anything measurable in exchange.

**Unix domain sockets, evaluated as asked**: only relevant if the listener
and the plugin's caller both run as native Linux processes on the same
host — which is true for *neither* of this project's two real topologies
(cross-machine LAN case: obviously not same-host; today's Proton case: the
plugin runs as Wine/Windows code, and Wine's own AF_UNIX support for
Winsock does not bridge to a native Linux process's Unix-domain socket in
the way TCP loopback does — Wine emulates AF_UNIX-like behavior internally
for cross-process communication *within* a prefix, not as a general bridge
out to arbitrary native Linux sockets by path). UDS would only become live
if this project committed to native Linux builds of both the game
integration and the listener, which is not the deployment target Skyrim
modding gives you. Not a live option today; noted per the task's request
to investigate it, not adopted.

**A faster transport for the position-streamer's 1 Hz "hot" path
specifically, if that channel ever needs a lower-latency mode (e.g., a
future higher-frequency requirement)**: still doesn't argue for named
pipes given Section 1's cross-boundary blocker — a raw UDP or WebSocket
channel over the same loopback/LAN-reachable socket family HTTP already
uses would get most of the same latency benefit without giving up
cross-machine reach. Worth revisiting only if a real requirement for
sub-second position freshness emerges; nothing in this codebase's current
scope (`v0.2 real-time NPC scope`'s own 1Hz target) asks for that.

---

## 5. When this recommendation would flip

State honestly, since the task asked for a structure the owner can
disagree with: this analysis's blocking objection (Section 1) evaporates
if a concrete future decision fixes the deployment to **one single real
Windows machine, running the game natively (no Proton/Wine) with the
Python service also running natively on that same box (not WSL, not a
separate machine)**. In that world, named pipes' lower per-message
overhead and OS-ACL-based auth become real, available benefits, and the
2-3x code-size migration cost in Section 3 might be worth paying —
though even then, Section 2's finding stands: nothing about this
project's actual 1.5 req/sec, sub-KB-payload cadence needs that lower
overhead today. That would be a "more idiomatic, not currently justified
by a measured need" call, which is a legitimate stated preference to make
deliberately — just not one this analysis can make for the owner, since it
depends on a deployment commitment (never Proton, never LAN-split) that
nothing in this repo currently states as a goal, and the repo's own dev
tooling (`tools/launch-chronicledev-skse.sh`, the DevBench SSH-tunnel
precedent) actively points the other way.

## What I could not determine without a live test

- Whether any Wine/Proton escape hatch exists for bridging a native Linux
  process into a Wine prefix's named-pipe namespace beyond what's
  documented above (running the listener inside the same prefix). I found
  no evidence of one in this project's research or in the three AI-NPC
  framework precedents it already studied, but a negative from research
  alone isn't the same as testing it live against a running GE-Proton
  prefix.
- Actual measured loopback HTTP round-trip latency on this specific dev
  machine/Proton setup (the ms figures above are well-established general
  loopback-HTTP characteristics, not a number pulled from this project's
  own telemetry — none exists, since nothing currently instruments
  request latency here).
