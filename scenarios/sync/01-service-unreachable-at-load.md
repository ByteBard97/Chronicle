# Scenario: service unreachable at load

**Setup**: a save with a valid manifest; the external service is down or
unreachable when the shim sends HELLO (`SYNC_TIMELINE`).

**Trigger**: player loads the save.

**Expected outcome**: the loading screen and gameplay proceed normally —
no stall waiting for a response. Outbound events are buffered locally in
a bounded queue (spilling to disk if the queue fills). When the service
becomes reachable again, the shim replays the buffer; the service
validates each buffered event against its ACKed branch head as if
received live, discarding anything stale per the epoch-fencing rule.

**Assert**: (1) no observable gameplay stall attributable to the sync
layer; (2) after reconnect, the service's branch state matches what it
would be had the connection never dropped, modulo ordering; (3) no event
is silently lost.

**Source**: ADR-0005's DEGRADED mode; `docs/research/09-save-sync-forensics.md`
§5.4 failure matrix, "Service down at load."
