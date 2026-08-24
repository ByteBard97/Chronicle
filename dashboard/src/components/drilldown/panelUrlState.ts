/**
 * Drill-target encoding within the existing `panels` URL codec
 * (`state/urlState.ts`'s `stringArrayCodec` — plain comma-joined strings,
 * each `encodeURIComponent`-escaped independently, confirmed pre-dispatch
 * to already carry a composite string with zero codec changes). One entry
 * of the form `drill:<beliefId>` represents the open provenance panel's
 * target; at most one such entry is ever present (opening a new drill
 * target replaces any existing one — it doesn't stack, matching the
 * pinned "same ProvenancePanel component ... one at a time" shape). Every
 * other `panels` entry (e.g. a future pinned-inspector id) passes through
 * untouched by these helpers.
 */
const DRILL_PREFIX = "drill:";

/** The currently open drill target's belief id, or `null` if no drill entry is present. */
export function parseDrillTarget(panels: string[]): string | null {
  for (const p of panels) {
    if (p.startsWith(DRILL_PREFIX)) return p.slice(DRILL_PREFIX.length);
  }
  return null;
}

/** `panels` with the drill entry set to `beliefId` (replacing any existing one). */
export function withDrillTarget(panels: string[], beliefId: string): string[] {
  return [...panels.filter((p) => !p.startsWith(DRILL_PREFIX)), `${DRILL_PREFIX}${beliefId}`];
}

/** `panels` with any drill entry removed. */
export function withoutDrillTarget(panels: string[]): string[] {
  return panels.filter((p) => !p.startsWith(DRILL_PREFIX));
}
