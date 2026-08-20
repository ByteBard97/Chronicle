# Scenario: death-retry resolves silently; a large jump is confirmed

**Setup A (death-retry)**: player dies, reloads the most recent
autosave/quicksave from seconds-to-minutes earlier, on the same branch.

**Setup B (large jump)**: player deliberately loads a save from a much
earlier point — hours or days of `gamets` behind the branch head.

**Trigger**: the load, in each case.

**Expected outcome**: Setup A resolves as an automatic CONTINUE or small
FORK with **no player-facing prompt** — death-retry must never interrupt
the player. Setup B resolves as a FORK with an **optional confirmation**
prompt (mirroring SkyrimNet's own `ClearTimelineMessage`/`msgClearHistory`
UX for its own rollback), since a jump this size plausibly represents a
deliberate return to an old save the player should be aware is diverging
Chronicle's world state.

**Assert**: (1) Setup A never shows a prompt, regardless of how many
times it repeats; (2) Setup B shows a prompt only above a configured
`gamets` divergence threshold, not on every reload; (3) declining the
Setup B prompt (if offered) still results in a safe, defined outcome —
never an unhandled state.

**Source**: `docs/research/09-save-sync-forensics.md` §4.2, §5.2 ("Two
details carry most of the reliability... the confirmation prompt is
reserved for *large* divergences").
