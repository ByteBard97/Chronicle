/**
 * useDrillPanel — the drill-down's open/target state, synced into the
 * existing `panels` URL codec (`panelUrlState.ts`'s `drill:<beliefId>`
 * entry). A thin composable, mirroring `useSelectionUrlSync`'s idiom
 * (installed from a host screen's `<script setup>` where `useUrlState()`'s
 * `useRouteQuery` has a safe component effect scope to attach to) but
 * simpler: the drill target has exactly one writer (the host's own drill
 * clicks / the panel's own close button) rather than two independent
 * writers needing loop-avoidance, so a plain read/write pair over
 * `urlState.panels` is enough — no `watch` needed.
 *
 * Every host screen (`FeedScreen.vue`, `MapScreen.vue`,
 * `VariantTreeScreen.vue`) calls this once and mounts one
 * `ProvenancePanel` bound to its `open`/`beliefId`.
 */
import { computed } from "vue";
import { useUrlState } from "../../state/urlState";
import { parseDrillTarget, withDrillTarget, withoutDrillTarget } from "./panelUrlState";

export function useDrillPanel() {
  const urlState = useUrlState();

  const beliefId = computed(() => parseDrillTarget(urlState.panels.value));
  const open = computed(() => beliefId.value !== null);

  function openDrill(id: string): void {
    urlState.panels.value = withDrillTarget(urlState.panels.value, id);
  }

  function closeDrill(): void {
    urlState.panels.value = withoutDrillTarget(urlState.panels.value);
  }

  return { beliefId, open, openDrill, closeDrill };
}
