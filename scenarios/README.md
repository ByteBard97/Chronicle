# scenarios

Regression scenarios with asserted outcomes. Each scenario seeds the event
log with a scripted sequence of inputs and asserts on the derived state some
number of ticks later — this is how the sim gets validated headless, without
the game running.

The north-star scenario (see `docs/vision.md`) is the Jarl of Whiterun
assassination: seed the death event, run N ticks, assert the succession
contest, economic ripple, mutated rumor spread, and infrastructure
consequences all land within expected bounds. `docs/v0.1-spec.md` scopes
v0.1's payoff to a minimal, provable slice of that: belief formation,
mutation across retellings, and evidence-chain traceability, without the
succession/economic/patrol consequences (deferred to later milestones).

| Scenario | Covers |
|---|---|
| [test_jarl_death_belief_cascade.py](test_jarl_death_belief_cascade.py) | witness -> mutated retelling (x2) -> evidence chain back to the canonical event (v0.1 payoff, spec §3) |

`scenarios/sync/` is a separate set of stub specs for the save/reload
sync handshake, not yet executable — see its own README.
