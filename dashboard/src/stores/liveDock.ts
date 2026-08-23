import { defineStore } from "pinia";

/**
 * LIVE dock state (ui-spec §1.3 / §2): "the view follows the newest
 * complete record when the playhead is docked at LIVE and detaches into
 * history the moment the user scrubs. One code path, two behaviors." —
 * and the approved chrome text this store's fields exist to drive:
 * `LIVE — docked · following newest frame · +N events · scrub to detach`.
 *
 * Stub-shaped like `selection.ts`/`salience.ts`: typed store, no view reads
 * it yet beyond this lane's minimal chrome readout (`src/stores/frameLog.ts`
 * and `Shell.vue`'s smoke-test wiring) — the timeline widget (Tier 2) is
 * the eventual primary consumer.
 */
export const useLiveDockStore = defineStore("liveDock", {
  state: () => ({
    /** True while following the newest frame; false once the user has scrubbed to a historical T. */
    docked: true,
    /** New records tailed in since the last count reset — the "+N events" the docked text reports. */
    newEventCount: 0,
  }),
  getters: {
    /**
     * Only the *docked* form is frozen verbatim by the work packet:
     * "LIVE — docked · following newest frame · +N events · scrub to
     * detach". The detached form isn't given a literal string anywhere
     * in ui-spec §2 or the work packet — this is a reasonable read of the
     * same fields for that state, not a second frozen contract; whichever
     * lane builds the timeline widget (Tier 2, the eventual primary
     * consumer of this store) should treat only the docked string as
     * load-bearing.
     */
    statusText: (state) =>
      state.docked
        ? `LIVE — docked · following newest frame · +${state.newEventCount} events · scrub to detach`
        : `LIVE — detached · +${state.newEventCount} events since detaching · scrub to LIVE to resume`,
  },
  actions: {
    /** The user scrubbed away from LIVE — detach and start counting what they're missing. */
    detach() {
      this.docked = false;
      this.newEventCount = 0;
    },
    /** The user asked to jump back to LIVE (or the playhead naturally reached the newest tick again). */
    dock() {
      this.docked = true;
      this.newEventCount = 0;
    },
    /** New records arrived from the LIVE tail poller, docked or detached. */
    recordNewEvents(count: number) {
      this.newEventCount += count;
    },
  },
});
