import { defineStore } from "pinia";

/**
 * The global selection model (ui-spec §2, GAMA's highlight-across-views):
 * one selection, shared by every view. Selection lives in the URL (`sel`) —
 * this store is the in-memory mirror components read/write; the shell wires
 * it to `useUrlState().sel` (M1 does not build that wiring's UI, just the
 * typed stub, per the work packet).
 *
 * Stub only: no view reads this yet. Typed so later lanes don't invent a
 * second selection model.
 */
export const useSelectionStore = defineStore("selection", {
  state: () => ({
    /** Entity ids in the current global selection (NPCs today; other kinds later). */
    selectedIds: [] as string[],
    /** The entity a "follow" toggle (ui-spec §2) is currently tracking, if any. */
    followedId: null as string | null,
  }),
  getters: {
    isSelected: (state) => (id: string) => state.selectedIds.includes(id),
  },
  actions: {
    select(id: string) {
      this.selectedIds = [id];
    },
    toggle(id: string) {
      this.selectedIds = this.selectedIds.includes(id)
        ? this.selectedIds.filter((existing) => existing !== id)
        : [...this.selectedIds, id];
    },
    clear() {
      this.selectedIds = [];
    },
    follow(id: string | null) {
      this.followedId = id;
    },
  },
});
