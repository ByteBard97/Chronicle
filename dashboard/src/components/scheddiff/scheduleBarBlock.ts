/**
 * The per-block render model `ScheduleBlockBar.vue` and `ScheduleLaneRow.vue`
 * share: a `derived/scheduleDiff.ts` block plus a highlight `state`, computed
 * once by `ScheduleLaneRow.vue` from a `NpcScheduleDiff`'s `before`/`after`/
 * `inserted`/`removed` lists (lane 41, ui-spec §3.8).
 */
import type { ScheduleDiffOverlayBlock } from "../../derived/scheduleDiff";

export type ScheduleBlockState = "unchanged" | "inserted" | "removed";

export interface ScheduleBarBlock {
  locationId: string;
  startTick: number;
  endTick: number;
  state: ScheduleBlockState;
  /** Present only when `state === "inserted"` -- the causal link ui-spec §3.8 names. */
  overlay?: Pick<ScheduleDiffOverlayBlock, "cause" | "rule" | "recordTick" | "triggerEventKey">;
}
