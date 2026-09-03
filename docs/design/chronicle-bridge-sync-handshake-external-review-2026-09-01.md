# Review — ChronicleBridge sync-handshake spec (2026-09-01)

**Reviewer:** Kimi (coordinator session), with live web/GitHub verification enabled.
**Subject:** `docs/design/chronicle-bridge-sync-handshake-out.md` (the "spec" below).
**Method:** read the spec against the actual repo (`chronicle/sync.py`, `chronicle/events.py`,
`adapters/skyrim/ChronicleBridge/`, `adapters/skyrim/listener/listener.py`, ADR-0004/0005,
`scenarios/sync/`), and re-verified every externally cited GitHub claim against the live sources.

Verdict up front: the spec's SKSE-API homework is real and checks out, the three already-fixed
bugs stay fixed, and the never-block instinct is right. But the spec is **not ready to implement**
in its current form: it re-specifies service-side logic that already exists and is tested, its
model of ChronicleBridge's HTTP client is factually wrong, and there are three coherence holes
(ACK-vs-commit semantics, gap-replay vs. Revert-drop, `confirm_required` having no meaning) that
would produce silent timeline corruption or dead-end implementation if coded as written.

---

## Part 1 — Adversarial technical review

### A. Blocking issues

**A1. §4.2 re-implements code that already exists — and contradicts it.**
The spec says RESOLVE will be "implemented server-side ... directly as a Python `match`/`if`-chain"
in `listener.py`, and its preamble claims "nothing in this doc exists in code yet." Neither is
true of the service half. `chronicle/sync.py` (330 lines, tested in `chronicle/tests/test_sync.py`)
already implements:

- `resolve(manifest, branch_state)` — the six-decision table, **plus a seventh case the spec
  doesn't know about**: known branch but manifest `head_seq` *ahead of* the service's → ADOPT
  (docstring cites scenario 02 explicitly).
- `mutation_admissible()` — the epoch-fencing predicate (ADR-0005 item 4).
- `SUPPORTED_FORMAT_VERSION = 1` — the version-too-new → LEGACY_IMPORT path (spec §5 row 04).
- Dedup on `(save_uuid, generation, seq)` — delegated to `EventLog.append()`, which is already
  idempotent with exactly that key (`events.py:206-214`).

There is also an existing design doc, `docs/design/chronicle-sync-cli-integration.md`, for wiring
`resolve()` into a real path — the spec doesn't cite it. As written, §4.2 would produce a second,
divergent RESOLVE table in the listener. **Fix:** the `/hello` handler must *call*
`chronicle.sync.resolve()`; `_SyncState` is only the session/epoch wrapper `sync.py` explicitly
leaves to the caller (`sync.py:291-301`). The spec's status header and §5 table should be
corrected to say what is actually built vs. what this spec adds (transport, session state, C++
shim, GC).

**A2. The spec's model of the existing HTTP client is partially wrong (§4, §4.1).**
*(Self-audited 2026-09-01, second pass — the "first round-trip" bullet in the original version of
this finding was overstated; see Corrigendum 2 at the bottom. What follows is the corrected text.)*
Spec: "the existing listener HTTP client pattern in ChronicleBridge already does this
[asynchronous fire] ... ACKs land on whatever thread the HTTP client's callback fires on."
Reality (`OutboundClient.cpp:687-698`, `OutboundClient.h:70-75`): cpp-httplib, **fully
synchronous**, no async API, no callbacks — a fresh `httplib::Client` per request with
1s connect/write/read timeouts, "asynchrony" achieved purely by running the blocking call on a
dedicated sender thread. Consequences the spec hasn't priced in:

- HELLO/RESOLVE is the **first request/response round-trip in the entire plugin** — every existing
  post is fire-and-forget and ignores the response body. There is no response-parsing precedent,
  and the JSON layer is hand-rolled with loud "NOT a general JSON parser" caveats
  (`OutboundClient.cpp:14-463`). The RESOLVE response (`decision` enum strings, nullable
  `resume_from_seq`, bool) must be parsed by that hand-rolled code — that's real, unbudgeted work.
- The "callback thread" is actually "the single sender thread that made the blocking call," which
  *simplifies* the `acked_head_seq` single-writer story (A4 below) but the spec's wording would
  mislead an implementer into looking for a callback mechanism that doesn't exist.
- The proposed 3s HELLO timeout (§4.3) conflicts with the established 1s per-request timeout
  convention. If HELLO reuses the existing config/client pattern, you get 1s, not 3s. Either is
  defensible; the spec must pick knowingly (see §7.3 below).

**A3. `_SyncState` cannot live in the listener's in-memory dicts — durability hole.**
The spec says `_SyncState` follows the existing `_HydrationPairState`/`_AvoidancePairState`
pattern. But every one of those is a closure-scoped dict that **does not survive a listener
restart** (listener.py:916-935) — which is fine for them, because their state is *recomputable*
by re-polling the run's frame log, and a dropped ack just re-offers. Branch/epoch/head state is
not recomputable from anything the listener reads. After a listener restart, service `head_seq`
resets to 0 while the co-save manifest says N; the next HELLO then resolves as ADOPT/LEGACY-flavored
amnesia (or hits `sync.py`'s seventh case), and ADR-0005 item 8's uncommitted buffer evaporates
while the shim believes those seqs are ACKed. Unlike every other slice, a listener restart here is
**silent timeline corruption**, not a soft retry. **Fix:** `_SyncState` (and the item-8 commit
buffer, or at least its watermark) must be durable — e.g., persisted under `runs/` or a sidecar
keyed by `save_uuid` — with a test: restart listener, HELLO the same manifest, assert CONTINUE.
This also reframes open question #5 (below).

**A4. `head_seq` conflates "ACKed" with "committed" — the item-8 buffer makes saves able to
reference state the service can lose.** ADR-0005 defines manifest `head_seq` as "last
service-ACKed ... so a save can never reference uncommitted state," and the spec repeats this
(§3 table). But item 8 says events sit in a *volatile* service-side buffer until `SAVE_CREATED`
commits them. If a mutation ACK advances `acked_head_seq` while the event only sits in the volatile
buffer, then: service crashes after ACKs but before `save-created` → events lost; next save writes
`head_seq = N` anyway; next load → CONTINUE, `resume_from_seq = N`, and the shim's Revert-drop
means the events are gone from both sides. Silent loss of committed-looking history. Additionally,
`save-created` is fire-and-forget (§4): if it's lost, the manifest claims a commit the service
never performed. **Fix (pick one, and write it down):** (a) mutation ACKs only advance
`acked_head_seq` if events are durably appended on receipt (move the commit point to the mutation
endpoint; item 8's buffer then only gates *derived-state visibility*, not durability); or (b) keep
two watermarks — `acked_head_seq` and `committed_head_seq` — with the manifest writing only the
latter, advanced by a `save-created` 2xx (which then can't be fire-and-forget). Note that
`sync.py`'s seventh case (manifest ahead of service → ADOPT) is the standing partial mitigation
for the residue — the spec's §5 row 02 should cite it rather than presenting scenario 02 as wholly
open.

**A5. ADR-0005's CONTINUE row assumes a replay capability the spec explicitly destroys.**
ADR-0005 row 1: CONTINUE → "replay any un-ACKed gap events." §4 of the spec defines
`resume_from_seq` in the opposite direction ("events the service already has past `head_seq`
don't need to be resent" — i.e., *shim* resumes streaming *to* the service), and §4.1's
OnGameRevert **drops the outbound queue**, so after any reload the shim retains nothing to replay
with. Net effect: a CONTINUE with a service-side gap (e.g., the A4 crash case) is unrecoverable as
specced — and nobody says so. The spec must pick and state one: (a) the DEGRADED spill file is
durable across reloads, keyed by `(save_uuid, generation)`, and Revert does *not* wipe it (this
contradicts §4.1 as written, and needs its own GC); (b) amend ADR-0005's CONTINUE row to drop the
"replay gap events" promise and declare post-reload gaps abandoned-by-design (honest, but weakens
the event-sourcing guarantee); or (c) make the *service* the replay source for gap events (it has
them — but then the loaded game world doesn't, which is FORK semantics, not CONTINUE). This is
the deepest semantic hole in the spec; scenario 09's closure claim depends on it.

**A6. `confirm_required` has no coherent semantics (§4, §7.2, scenario 11).**
The flag exists in the RESOLVE response, but the spec never says: who renders the prompt
(SKSE MessageBox on the main thread? Papyrus?), what happens to events while it is pending, or —
the killer — **what declining means**. By `kPostLoadGame` the load has already happened; the game
world has already rolled back. You cannot un-fork world state. The only things a "confirm" can
govern are service-side record-keeping, or an offer to load the newest save. As specced, an
implementer will either invent semantics on the spot or ship a dead flag. **Recommendation:** for
v1, replace the confirm dialog with a non-modal notification plus a dashboard-visible audit record
of every FORK (silent or not); defer interactive confirm until someone can state what the "no"
branch does. See §7.2 below for the threshold itself.

### B. Races and thread-safety

**B1. The spec fixed the `acked_head_seq` race and then introduced the same race twice more.**
§4.1 declares `g_isLoading: bool` and `epoch_id: uint64` as plain variables. Both are written
from the sender thread (HELLO response / timeout → DEGRADED) and read from the main thread
(save callback, event gates) and the poller threads. The spec's own reasoning for making
`acked_head_seq` a `std::atomic<uint64_t>` applies verbatim to these two. Make all three atomics
(or one mutex-guarded state struct). A C++ reviewer will catch this in review; better to catch it
here.

**B2. No HELLO generation counter — quickload spam can apply a stale RESOLVE.**
Sequence: `kPreLoadGame` → HELLO A in flight; player quickloads again before it answers → Revert
wipes state → HELLO B fires. A and B are both in flight; **A's response arriving after B's
overwrites `epoch_id` with the previous load's epoch** — precisely the silent wrong-epoch
condition epoch fencing exists to prevent, reintroduced at the handshake layer. Add a monotonic
`hello_seq` incremented per `kPostLoadGame`; discard any response whose tag isn't current. The
DEGRADED backoff-retry loop needs the same discipline: it must be cancelled on
`kPreLoadGame`/Revert, or a retry from the previous load lands mid-new-load. Neither is specified.

**B3. Mutation-409 handling is unspecified on the shim side.**
§4 says the service rejects stale-epoch mutations with 409. What does the shim *do* with a 409?
Drop the event (data loss)? Re-HELLO (livelock risk during epoch churn)? Count and go DEGRADED?
This is the fencing mechanism's recovery path and it's currently a blank. Minimum: drop the
rejected event, log loudly, increment a counter, and re-HELLO if 409s persist beyond N — stated
in the spec.

**B4. NEW_TIMELINE skips the HELLO, leaving epoch 0 overloaded (§4.1 `kNewGame`).**
No HELLO means: the service never learns the branch exists until the first mutation; epoch 0 is
both "legitimate genesis epoch" and "DEGRADED placeholder"; the fencing rule ("reject epoch older
than active") is undefined for an unknown branch; and a player who saves immediately (common —
the Helgen intro autosaves) sends `save-created` for a branch the service has never seen.
Cheapest fix: send the HELLO on `kNewGame` too — "nothing to resolve against" is itself a
resolvable fact (the NEW_TIMELINE row exists). Alternatively, explicitly define epoch 0 as the
universal genesis epoch and define unknown-branch mutation/save-created semantics in §4.2.

### C. Wire format / ABI

**C1. [SUPERSEDED — see Corrigendum 1; my arithmetic here was itself wrong, and the spec's own
byte total is wrong in a way my original text missed.]**
Original text retained for the record: field order in §3 (magic 4B, `save_uuid` 16B, then six
8-byte fields) puts the first `uint64_t`
at offset 20 — under natural alignment `sizeof(Manifest)` is 64, not 60, and the Load-side
`a_length == sizeof(Manifest)` check either fails against its own writer or, worse, passes on one
build and fails on another. Fix: `#pragma pack(push, 1)` + `static_assert(sizeof(Manifest) == 60)`,
or reorder (8-byte fields first, `save_uuid`, magic last) so natural alignment yields 60. Also
check `ReadRecordData`'s return value against 60, not just `GetNextRecordInfo`'s length.

**C2. The `'CHRN'` hex constant is byte-swapped — the exact error the spec warned about.**
§7.1: "'CHRN' (`0x4E524843` little-endian...)". A C++ multichar literal `'CHRN'` has the value
`0x4348524E` on every platform (compare §3's own `'CHRC'` = `0x43485243`, computed correctly).
`0x4E524843` is the byte-reversed value. The collision check against the cosave-cleaner catalog
must use `0x4348524E` (the catalog displays "big-endian FourCC, matching how devs write them in
C++" — its JContainers entry is `0x4A535452` = `'JSTR'`, consistent). Conclusion unchanged —
neither value appears in the catalog — but a spec that says "check the codebase's byte-order
conventions" should not ship its own endianness bug. Notably, Soulsy writes its record type as
`_byteswap_ulong('CYCL')`, i.e., real projects trip on exactly this.

**C3. Type/unit mismatches with the existing Python side.**
- `chronicle/sync.py`'s `Manifest.save_uuid` is `str`, and existing `save_uuid`s are
  human-readable (`"save-listener-1"`, `"livetest-<run_id>"`). The spec's `uint8_t[16]` UUIDv4 +
  32-char hex wire form needs a canonical mapping — and a stated answer for what happens to
  non-UUID `save_uuid`s already sitting in existing runs (LEGACY_IMPORT them? migrate?).
- `chronicle/events.py` `wall_ts` is a **float** (seconds); the spec's manifest `wall_ts` is
  `int64` Unix **milliseconds**. A 1000× unit skew in transaction time is the kind of bug that
  passes every test that doesn't look at wall_ts directly. Pin the unit conversion at both ends
  in the spec.

### D. Smaller gaps worth fixing while you're in there

- **D1.** §4.1 gates "all per-slice event-generation hooks" on `g_isLoading`. The existing
  architecture already funnels everything through mutex'd sender queues; gating the *drain* (the
  sender threads) is less invasive and less race-prone than touching every sink. Either works;
  the spec should pick the drain.
- **D2.** The DEGRADED spill-to-file (§4.3): which thread does the file I/O (main-thread disk
  writes during gameplay would be a quiet never-block violation), and Revert must delete/rotate
  the spill file, not just drop the ring (§4.1 only mentions the ring) — otherwise stale
  pre-reload events replay into the new branch.
- **D3.** OnGameRevert's "g_isLoading stays true (Load/kPostLoadGame haven't run yet)" assumes
  Revert only fires mid-load. Revert also fires on quit-to-main-menu with no subsequent load —
  harmless here (nothing gates on it at the menu), but the comment's invariant is wrong. Also
  note Revert does *not* fire on the first load after process start (no session to revert), so
  initial-state cleanliness must come from construction defaults, not from the Revert handler —
  §5 row 06's reasoning should say this.
- **D4.** §6's test plan lists "DEGRADED buffering path (assert the ring buffer fills and
  replays)" as a `test_listener.py` case. The ring buffer is C++-side; Python cannot test it. The
  project has **no C++ test harness at all**, so the riskiest component (the SyncHandshake state
  machine) currently has no unit-test story. Either structure `SyncHandshake.cpp` so the state
  machine is a pure transition function over inputs (mirroring how `sync.py`'s `resolve()` is a
  pure classification function — that's what made it testable) or downgrade the claim.
- **D5.** `kSaveGame` vs. the Save callback: the spec should pin that `save-created`'s
  `committed_through_seq` is the *same* atomic read as the manifest's `head_seq` (or sampled once
  in the Save callback and reused), else the two can skew under concurrent ACKs.
- **D6.** The ship-gate paragraph (§6, FORK unverifiable until the `action=load` bug clears) is
  exactly the right kind of honesty — keep it, and note the harness already has a working
  `loadLast` workaround documented in `livetest/test_30_hydration.py:75-89` that may partially
  unblock live reload testing (by-name `load` no-ops; `loadLast` works).

---

## Part 2 — Spot-check of cited research claims

| Claim in spec | Verification result |
|---|---|
| CommonLibSSE-NG `Interfaces.h`: `Message` struct has no `success` field; enum names; `SerializationInterface kVersion = 4`, `MessagingInterface kVersion = 2`; method signatures | **Verified verbatim** against `CharmedBaryon/CommonLibSSE-NG@main`. The §0 correction to ADR-0005 is right. |
| JContainers hardcodes `'JSTR'` (`0x4A535452`) for both `SetUniqueID` and its record type (`src/jcontainers_constants.h`) | **Verified** (`develop` branch): `storage_chunk = 'JSTR'`, used for both `SetUniqueID` and `OpenRecord` in `skse_callbacks.cpp`. Minor caveat: it's the old SKSE64 API shape (`SetUniqueID(pluginHandle, uid)`) — irrelevant to the claim. |
| JContainers `revert()` calls `domain_master::master::instance().clear_state()` | **Verified** (`skse_callbacks.cpp`). |
| Soulsy `revertHandler` is a one-line `clear_cache()` | **Verified verbatim** (`ceejbot/soulsy`, branch `latest`, `src/plugin/cosave.cpp`: `void revertHandler(SKSE::SerializationInterface*) { clear_cache(); }`). |
| Soulsy defaults to `'SOLS'`, player-configurable via INI `sSKSEIdentifier` | **Verified** (`src/controller/settings.rs`: default `"SOLS"`, `read_from_ini(..., "sSKSEIdentifier", ...)`). Bonus detail: Soulsy byteswaps its FourCCs (`_byteswap_ulong('CYCL')`) — see C2. |
| spookys-cosave-cleaner `KNOWN_PLUGINS` ~18 entries, incl. non-ASCII hashes, no `'CHRN'` | **Verified** (`skse_cosave_cleaner.py`: 24 entries actually, incl. `0x424510A2` PapyrusUtil, `0xA0B0D9EE` unknown; `'CHRN'` absent in either byte order). |
| Mfg-Fix-NG: C++ but stateless, no `SetUniqueID` | **Verified** (no `SetUniqueID`/`SerializationInterface` anywhere in `KrisV-777/Mfg-Fix-NG@main`). |
| CHIM game-side plugin has no public source; only satellite tools public under Dwemer-Dynamics | **Verified** (org repo listing: server, installer, dashboard, TTS/STT bridges, etc. — no game plugin). |
| "CHIM PR #572" unverifiable | **Confirmed unverifiable**: `Dwemer-Dynamics/HerikaServer` issues/PRs #572 and #560 both return 404 today. The spec's "treat as unconfirmed" is correct. **Note for the board:** ADR-0004 leans on PR #572 as primary-source grounding for the mandatory-bitemporal rule; that grounding is currently anecdotal and should be footnoted as such in the ADR. |
| SkyrimNet's game-side plugin (`MinLL/SkyrimNet-GamePlugin`) "is pure Papyrus with no SerializationInterface use" | **Misleading as worded.** The public repo is indeed Papyrus + assets only, but SkyrimNet itself is a closed-source native DLL — its own README: "SkyrimNet is… a native Windows DLL that loads inside Skyrim itself" — and the Beta20 release notes say voice-effect assignments are "persisted to the SKSE cosave," i.e. its game side **does** use the co-save. Correct rewrite: "SkyrimNet's native plugin is closed-source, so its co-save usage can't be studied." That *strengthens* the spec's "no positive precedent exists" point — the honest claim is better than the current one. |

Summary: one material mischaracterization (SkyrimNet), one numeric slip (the `'CHRN'` hex), zero
fabrications. The research discipline ("here is the ceiling of due diligence available") is good
and the verified claims hold up.

---

## Part 3 — The five open questions

**§7.1 — FourCC.** Proceed with `'CHRN'`, but fix the constant (`0x4348524E`; C2) and adopt
Soulsy's mitigation now rather than as a fallback: ChronicleBridge already has
`Data/SKSE/Plugins/ChronicleBridge.ini` via `Config.cpp`, so making the uid an INI setting with
`'CHRN'` default is nearly free and turns a future collision report from a mod-update into a
config edit.

**§7.2 — "Large jump" threshold.** Recommendation: a two-signal OR rule, computed server-side at
RESOLVE, both constants INI-tunable, and **every FORK decision (silent or confirmed) logged with
its inputs to the run** so the dashboard can audit the policy:

- `confirm_required = (head_gamets − manifest.gamets) > 24 game-hours OR (head_seq − manifest.head_seq) > 50 events`
- gamets is in *hours* (`GetHoursPassed()`; timescale 20 means a death-retry is typically
  < 1 game-hour of lost progress; a deliberate return to an old save is usually days).
- The seq leg catches "30 intense minutes with 80 events"; the gamets leg catches "slept/waited
  3 days with nothing recorded." Either alone is gameable; the OR is not perfect but is honest.
- **Never** use `wall_ts` — real-time delta measures the player's lunch break, not the jump.
- But per A6: until someone specifies what declining a fork *does*, ship the threshold as
  notification-only. The threshold question is easier than the semantics question, and the spec
  has been treating the former as the blocker when the latter is.

**§7.3 — Timeouts.** Fine as tunables, but decide knowingly: the established per-request
convention is 1s. If HELLO deserves 3s (defensible — it's once per load, not steady-state), say
so and don't inherit the 1s default by reusing the client config blindly.

**§7.4 — Scope cuts.** Agree with both. Scenario 05 is genuinely a `chronicle/` state-store
concern. Scenario 02 stays residual-risk, but cite `sync.py`'s manifest-ahead-of-service → ADOPT
case as the standing partial mitigation rather than leaving the row reading as wholly unmitigated.

**§7.5 — `--live-run` gating.** Don't gate `/whiterun/sync/*` (keep the bearer token). Gating
would break the exact case the feature exists for — a real player's first launch, where no
`--live-run` demo run exists — and sync state is keyed by `save_uuid`, orthogonal to demo runs.
But the deeper issue is A3: the listener's entire model is "one developer-designated live run"
(ChronicleBridge README:62-66), with per-process memory that's recomputable *for the other
slices*. The sync handshake is the first feature whose state must outlive both the listener
process and any single run. That argues for putting branch/epoch state in `chronicle/` (durable,
adjacent to the run dir) with the listener as a thin transport — which is also the direction
`docs/design/chronicle-sync-cli-integration.md` already pointed. If that's too big for this
spec, the minimum viable version is: ungated + token auth + durable `_SyncState` sidecar, with
the listener-restart test from A3 in the test plan.

---

## What the spec gets right (so it survives revision)

- The §0 correction to ADR-0005, verified against the real header.
- The magic-sentinel + length + version triple-check on Load is the right defense-in-depth for
  the `SetUniqueID` collision hazard, and the reasoning (a_version can't detect a foreign plugin's
  same-length record) is sound.
- The Revert-handler addition, and the "drop the queue, it was never ACKed" rationale, correctly
  close scenario 06 (subject to D2/D3).
- The `acked_head_seq` atomic-read-at-save discipline is the right shape — extend it to
  `g_isLoading`/`epoch_id` (B1) and fix the ACK-vs-commit semantics (A4) and it's solid.
- The ship-gate honesty about FORK being unverifiable until the harness bug clears.
- The research methodology and its stated confidence ceiling — the claims I could check, checked
  out.


---

## Self-audit corrigenda (2026-09-01, second pass)

After writing the above, I re-verified every load-bearing claim directly against the repo and
re-ran my arithmetic. Four corrections, one of which turns out to be a *stronger* finding against
the spec than what I originally wrote:

**Corrigendum 1 — finding C1 was numerically wrong, and the spec's own byte total is also wrong
(missed the first time).** I claimed "natural alignment gives 64" and "reordering the fields
yields 60 naturally." Both false, verified with `ctypes`:

- The spec's field table sums to **64 bytes, not 56** (`save_uuid` 16 + **six** 8-byte fields
  = 16 + 48 = 64; the spec's "Total: 56 bytes" undercounts by 8). With the 4-byte magic, the real
  payload is **68 bytes, not 60**.
- Natural alignment (`uint64_t` at offset 20 padded to 24): `sizeof == 72`, not the 64 I wrote.
- Packed (`#pragma pack(1)`): `sizeof == 68`, not 60.
- **No field ordering yields 60 or 68 under natural alignment** (any layout containing 8-byte
  fields pads `sizeof` to a multiple of 8; 68 → 72). My "reorder to avoid packing" suggestion was
  impossible; packing is mandatory if the magic stays at offset 0.

The substantive finding is thereby *strengthened*: the spec's §3 check "reject unless
`a_length == 60`" would, if implemented as written, **reject every legitimate record the plugin
itself writes**, since the true record is 68 bytes. The spec must fix the field sum (64+4=68),
mandate `#pragma pack(push, 1)` with `static_assert(sizeof(Manifest) == 68)`, and use
`static_assert`-ed constants for the Load-side check rather than a hand-computed literal.
My FourCC arithmetic in C2, by contrast, re-verified exactly (`'CHRN'` = `0x4348524E`;
`'CHRC'` = `0x43485243`; the spec's `0x4E524843` is the byte-reversal — that finding stands).

**Corrigendum 2 — finding A2 overstated the JSON/round-trip gap.** I wrote that HELLO would be
"the first request/response round-trip in the entire plugin" with "no response-parsing precedent."
False: `OutboundClient.cpp` already does `client.Get(...)` with response-body parsing at four
sites (lines 477, 543, 603, 636 — `FetchHydrationPairs` and siblings), and the hand-rolled
`ParseJsonStringField/BoolField/IntField` family exists precisely for that. What remains true and
load-bearing: (a) there is **no callback mechanism** — all HTTP is blocking calls on dedicated
sender/poller threads, so §4.1's "whatever thread the HTTP client's callback fires on" describes
a thing that doesn't exist; (b) the 1s per-request timeout convention vs. the proposed 3s HELLO
timeout conflict stands; (c) all *POSTs* are fire-and-forget — HELLO is the first POST whose
response body matters; (d) the hand-rolled parser has **no `null` literal handling** —
`ParseJsonIntField` returns `std::nullopt` on a JSON `null`, which happens to be the right shape
for `resume_from_seq: uint64 | null` but conflates "null" with "key absent"; that should be a
deliberate choice in the spec, not an accident.

**Corrigendum 3 — KNOWN_PLUGINS count.** I wrote "24 entries actually"; the exact count is **23**
entries, of which ~20 are real mods (excluding the two `SKSE Core` pseudo-entries and the
`Unknown (A0B0D9EE)` placeholder). The spec's "~18" and my "24" were both approximations; the
collision conclusion (`'CHRN'` absent in either byte order) is unchanged.

**Corrigendum 4 — finding D3's Revert-timing aside was asserted, not verified.** I stated that
"Revert does not fire on the first load after process start." I could not verify that against any
authoritative source in this pass — it's SKSE folklore-level knowledge, exactly the class of claim
this spec (rightly) insists on flagging. Downgrade to: *"whether Revert fires on the very first
load of a process, and its exact ordering relative to `kPreLoadGame`/the Load callback, must be
verified empirically in the live harness before scenario 06's closure is claimed; initial-state
cleanliness should come from construction defaults regardless."* The D3 design point (don't rely
on the Revert handler for initial state) stands on its own without the timing claim.

**Verified as correct in the second pass** (no change): A1 (`sync.py`'s seventh case → ADOPT
confirmed at `sync.py:159-165, 204-213`; `SUPPORTED_FORMAT_VERSION = 1` at line 147;
`save_uuid: str` at line 45), A3, A4, A5, A6, B1–B4, C2, C3, D1, D2, D4, D5, D6, all of Part 2's
verified/refuted table entries (JContainers `develop` branch, Soulsy `latest` branch,
Mfg-Fix-NG, Dwemer-Dynamics org listing, HerikaServer #560/#572 both 404, SkyrimNet native-DLL
correction), and the Part 3 recommendations. The overall verdict stands.
