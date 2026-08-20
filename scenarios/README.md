# scenarios

Regression scenarios with asserted outcomes. Each scenario seeds the event
log with a scripted sequence of inputs and asserts on the derived state some
number of ticks later — this is how the sim gets validated headless, without
the game running.

The north-star scenario (see `docs/vision.md`) is the Jarl of Whiterun
assassination: seed the death event, run N ticks, assert the succession
contest, economic ripple, mutated rumor spread, and infrastructure
consequences all land within expected bounds.
