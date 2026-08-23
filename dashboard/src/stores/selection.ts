import { defineStore } from "pinia";

/**
 * The global selection model (ui-spec §2, GAMA's highlight-across-views):
 * one selection, shared by every view. Selection lives in the URL (`sel`) —
 * this store is a plain, view-agnostic, in-memory mirror with no
 * router/urlState imports (deliberately: `useUrlState()` wraps
 * `useRouteQuery`, which needs an active component/effect scope tied to
 * the router at call time — unsafe to call from inside a Pinia store
 * action). The two-way store <-> `urlState.sel` binding lives in
 * `src/state/useSelectionUrlSync.ts`, a composable each screen installs
 * from its own `<script setup>` (lane 11: FeedScreen installs it; the map
 * installs the same composable later, at M3 wiring).
 *
 * First real consumer: lane 11's encounter feed (row click -> both
 * participant ids selected). Typed so later lanes don't invent a second
 * selection model.
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
    /** Replace the whole selection at once (e.g. a feed row's two participants). */
    selectMany(ids: string[]) {
      this.selectedIds = [...ids];
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
