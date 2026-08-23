/**
 * Salience -> display-item projection for the encounter feed (ui-spec §2 /
 * lane-11 packet's "Key design facts" — pinned semantics):
 *
 *  - Story: transmissions + declines only.
 *  - Observer: transmissions + declines at full weight; trace rows
 *    (rolled-against, nothing-salient) collapsed into one per-tick
 *    group-header item, expandable in place (view-local `expandedTicks`,
 *    NOT url state).
 *  - Developer: the full row set, no group chrome.
 *  - `showAll` (the list-level "all events" escape hatch, every level):
 *    always renders the full Developer row set regardless of the current
 *    salience level.
 *
 * Pure and independently testable — no store/component coupling.
 */
import type { SalienceLevel } from "../../stores/salience";
import type { FeedRow } from "../../log/feedReader";

export type FeedDisplayItem =
  | { type: "row"; row: FeedRow }
  | { type: "group"; tick: number; rows: FeedRow[] };

const TRACE_OUTCOMES = new Set(["rolled_against", "nothing_salient"]);
const HEADLINE_OUTCOMES = new Set(["transmitted", "declined"]);

function isTraceRow(row: FeedRow): boolean {
  return TRACE_OUTCOMES.has(row.outcome);
}

/** Flat: every row rendered individually, no grouping/filtering by outcome. */
function flatItems(rows: FeedRow[]): FeedDisplayItem[] {
  return rows.map((row) => ({ type: "row", row }));
}

/** Story: headline rows (transmitted/declined) only. */
function storyItems(rows: FeedRow[]): FeedDisplayItem[] {
  return rows.filter((row) => HEADLINE_OUTCOMES.has(row.outcome)).map((row) => ({ type: "row", row }));
}

/**
 * Observer: headline rows stay individual; runs of consecutive trace rows
 * sharing the same tick collapse into one group item — unless that tick is
 * in `expandedTicks`, in which case its trace rows render individually
 * in place (chronology/scroll position preserved either way).
 */
function observerItems(rows: FeedRow[], expandedTicks: ReadonlySet<number>): FeedDisplayItem[] {
  const items: FeedDisplayItem[] = [];
  let i = 0;
  while (i < rows.length) {
    const row = rows[i];
    if (!isTraceRow(row)) {
      items.push({ type: "row", row });
      i += 1;
      continue;
    }
    const tick = row.tick;
    const group: FeedRow[] = [];
    while (i < rows.length && rows[i].tick === tick && isTraceRow(rows[i])) {
      group.push(rows[i]);
      i += 1;
    }
    if (expandedTicks.has(tick)) {
      for (const groupRow of group) items.push({ type: "row", row: groupRow });
    } else {
      items.push({ type: "group", tick, rows: group });
    }
  }
  return items;
}

export function buildDisplayItems(
  rows: FeedRow[],
  salience: SalienceLevel,
  showAll: boolean,
  expandedTicks: ReadonlySet<number>,
): FeedDisplayItem[] {
  if (showAll) return flatItems(rows);
  if (salience === "developer") return flatItems(rows);
  if (salience === "story") return storyItems(rows);
  return observerItems(rows, expandedTicks);
}
