<script setup lang="ts">
/**
 * FeedTable — the virtualized encounter-feed table (`@tanstack/vue-virtual`,
 * this lane's first consumer of the already-installed dependency). Renders
 * a heterogeneous item list (`FeedDisplayItem`: plain rows in
 * Story/Developer, plus Observer's variable-height group-header rows) —
 * `measureElement` is what makes the group rows' real height count instead
 * of a fixed estimate.
 *
 * `scrollToTick` (if given, and found among `items`) scrolls that item
 * into the middle of the viewport once, right after this component mounts
 * — the mechanism behind the M2 deep-link landing cases (ui-spec §5's
 * developer twin: a negative-row deep link must land visible without
 * scrolling).
 */
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useVirtualizer } from "@tanstack/vue-virtual";
import FeedRowItem from "./FeedRowItem.vue";
import FeedGroupHeaderRow from "./FeedGroupHeaderRow.vue";
import type { FeedDisplayItem } from "./feedGrouping";
import type { FeedRow } from "../../log/feedReader";

const props = defineProps<{
  items: FeedDisplayItem[];
  selectedIds: string[];
  scrollToTick?: number | null;
}>();

const emit = defineEmits<{
  rowClick: [row: FeedRow];
  toggleGroup: [tick: number];
}>();

const scrollParent = ref<HTMLElement | null>(null);

function estimateSize(index: number): number {
  const item = props.items[index];
  return item?.type === "group" ? 26 : 30;
}

const virtualizer = useVirtualizer(
  computed(() => ({
    count: props.items.length,
    getScrollElement: () => scrollParent.value,
    estimateSize,
    overscan: 8,
  })),
);

const virtualItems = computed(() => virtualizer.value.getVirtualItems());
const totalSize = computed(() => virtualizer.value.getTotalSize());

function targetIndex(tick: number | null | undefined): number {
  if (tick === null || tick === undefined) return -1;
  return props.items.findIndex(
    (item) => (item.type === "row" && item.row.tick === tick) || (item.type === "group" && item.tick === tick),
  );
}

function scrollToTarget() {
  const idx = targetIndex(props.scrollToTick);
  if (idx >= 0) {
    virtualizer.value.scrollToIndex(idx, { align: "center" });
  }
}

onMounted(async () => {
  await nextTick();
  scrollToTarget();
});

watch(
  () => [props.scrollToTick, props.items.length] as const,
  async () => {
    await nextTick();
    scrollToTarget();
  },
);

function isSelectedRow(row: FeedRow): boolean {
  return row.participants.some((id) => props.selectedIds.includes(id));
}
</script>

<template>
  <div class="feed-table">
    <div class="feed-table__head" role="row">
      <span>tick</span>
      <span>location</span>
      <span>participants</span>
      <span>outcome</span>
    </div>
    <div ref="scrollParent" class="feed-table__scroll" data-testid="feed-table-scroll">
      <div class="feed-table__spacer" :style="{ height: `${totalSize}px` }">
        <div
          v-for="vrow in virtualItems"
          :key="String(vrow.key)"
          :ref="(el) => virtualizer.measureElement(el as Element)"
          :data-index="vrow.index"
          class="feed-table__vitem"
          :style="{ transform: `translateY(${vrow.start}px)` }"
        >
          <FeedGroupHeaderRow
            v-if="items[vrow.index].type === 'group'"
            :tick="(items[vrow.index] as Extract<FeedDisplayItem, { type: 'group' }>).tick"
            :rows="(items[vrow.index] as Extract<FeedDisplayItem, { type: 'group' }>).rows"
            :expanded="false"
            @toggle="emit('toggleGroup', $event)"
          />
          <FeedRowItem
            v-else
            :row="(items[vrow.index] as Extract<FeedDisplayItem, { type: 'row' }>).row"
            :selected="isSelectedRow((items[vrow.index] as Extract<FeedDisplayItem, { type: 'row' }>).row)"
            @row-click="emit('rowClick', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.feed-table {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.feed-table__head {
  display: grid;
  grid-template-columns: 64px 120px 200px 1fr;
  gap: 10px;
  padding: 4px 12px;
  border-bottom: 1px solid var(--c-hairline);
  color: var(--c-text-faint);
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.feed-table__scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  position: relative;
}

.feed-table__spacer {
  position: relative;
  width: 100%;
}

.feed-table__vitem {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
}
</style>
