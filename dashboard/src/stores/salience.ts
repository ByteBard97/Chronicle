import { defineStore } from "pinia";

/** The three global salience-filter defaults (ui-spec §2). */
export type SalienceLevel = "developer" | "observer" | "story";

export const SALIENCE_LEVELS: readonly SalienceLevel[] = [
  "developer",
  "observer",
  "story",
];

/**
 * The global salience filter (ui-spec §2): every raw list obeys this filter
 * and carries an "all events" toggle. Stub only — no view reads this yet.
 */
export const useSalienceStore = defineStore("salience", {
  state: () => ({
    level: "observer" as SalienceLevel,
    /** The "all events" escape hatch every filtered list must carry (ui-spec §2). */
    showAll: false,
  }),
  actions: {
    setLevel(level: SalienceLevel) {
      this.level = level;
    },
    setShowAll(showAll: boolean) {
      this.showAll = showAll;
    },
  },
});
