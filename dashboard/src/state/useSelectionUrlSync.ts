/**
 * Two-way binding: `useSelectionStore().selectedIds` <-> `useUrlState().sel`
 * (ui-spec §2: "Selection is in the URL"). Deliberately a composable, not
 * logic inside `stores/selection.ts` (that store has no router/urlState
 * imports on purpose — see its header comment) — installed from a
 * screen's `<script setup>` where `useUrlState()`'s `useRouteQuery` has a
 * safe component effect scope to attach to.
 *
 * Direction 1 (deep link -> store): a `sel` present on load, or changed by
 * back/forward navigation, is written into the store.
 * Direction 2 (store -> URL): a selection made in-app (e.g. a feed row
 * click) is pushed into `sel`.
 *
 * Both directions compare arrays before writing, so a round-trip (store
 * writes url, which the url->store watcher then observes) does not loop or
 * create a duplicate history entry.
 */
import { watch } from "vue";
import { storeToRefs } from "pinia";
import { useUrlState } from "./urlState";
import { useSelectionStore } from "../stores/selection";

function sameIds(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((id, i) => id === b[i]);
}

export function useSelectionUrlSync(): void {
  const urlState = useUrlState();
  const selection = useSelectionStore();
  const { selectedIds } = storeToRefs(selection);

  watch(
    urlState.sel,
    (ids) => {
      if (!sameIds(ids, selection.selectedIds)) {
        selection.selectMany(ids);
      }
    },
    { immediate: true },
  );

  watch(selectedIds, (ids) => {
    if (!sameIds(ids, urlState.sel.value)) {
      urlState.sel.value = [...ids];
    }
  });
}
