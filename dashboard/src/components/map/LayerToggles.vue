<script setup lang="ts">
/**
 * LayerToggles — the map layer chip panel from map-c-skyrim.dc.html:
 * 80-88: glyphs / labels / routes chips (checked) plus the unchecked
 * deviations chip, and the glyph-precedence caption. All four chips
 * actually toggle, via v-model up to MapView.
 *
 * Mockup ambiguity note: the mockup has exactly four chips and the
 * fixture's only remaining layer flag is `stainLens` — and the LENS
 * panel says "ONE OVERLAY ACTIVE". So the deviations chip is wired as
 * the stain-lens alternator: deviations checked ⟺ stainLens off
 * (markers fall back to the fixture's gray lens-off pair). glyphs /
 * labels / routes map straight onto their v-models.
 */
import { computed } from "vue";
import PanelGlass from "../PanelGlass.vue";

const showGlyphs = defineModel<boolean>("showGlyphs", { required: true });
const showLabels = defineModel<boolean>("showLabels", { required: true });
const showRoutes = defineModel<boolean>("showRoutes", { required: true });
const stainLens = defineModel<boolean>("stainLens", { required: true });

/** deviations overlay on ⟺ rumor-stage stain lens off (one overlay active). */
const deviationsOn = computed({
  get: () => !stainLens.value,
  set: (on: boolean) => {
    stainLens.value = !on;
  },
});

const chips = computed(() => [
  { key: "glyphs", label: "glyphs", on: showGlyphs.value },
  { key: "labels", label: "labels", on: showLabels.value },
  { key: "routes", label: "routes", on: showRoutes.value },
  { key: "deviations", label: "deviations", on: deviationsOn.value },
]);

function toggle(key: string) {
  if (key === "glyphs") showGlyphs.value = !showGlyphs.value;
  else if (key === "labels") showLabels.value = !showLabels.value;
  else if (key === "routes") showRoutes.value = !showRoutes.value;
  else if (key === "deviations") deviationsOn.value = !deviationsOn.value;
}
</script>

<template>
  <PanelGlass class="layer-toggles" :padded="false">
    <div class="layer-toggles__chips">
      <a
        v-for="chip in chips"
        :key="chip.key"
        href="#"
        class="layer-toggles__chip"
        :class="chip.on ? 'layer-toggles__chip--on' : 'layer-toggles__chip--off'"
        :data-layer="chip.key"
        @click.prevent="toggle(chip.key)"
      >
        {{ chip.on ? "✓" : "□" }} {{ chip.label }}
      </a>
    </div>
    <div class="layer-toggles__caption">
      glyph = worst case: deviation ▸ grudge ▸ spreading ▸ new belief
    </div>
  </PanelGlass>
</template>

<style scoped>
.layer-toggles {
  /* mockup border rgba(201,168,106,.18) == --c-hairline-soft */
  border-color: var(--c-hairline-soft);
  padding: 8px 11px 9px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.layer-toggles__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.layer-toggles__chip {
  padding: 2px 7px;
  border-radius: var(--radius-chip);
  white-space: nowrap;
}

.layer-toggles__chip--on {
  border: 1px solid var(--c-chip-active-border);
  /* mockup uses alpha .10 here; --c-chip-active-fill is .14 (token gap,
   * literal from map-c-skyrim.dc.html:82) */
  background: rgba(201, 168, 106, 0.1);
  color: var(--c-accent-hover);
}

.layer-toggles__chip--off {
  border: 1px solid var(--chip-muted-border);
  color: var(--c-text-dim);
}

.layer-toggles__caption {
  color: var(--c-text-dim);
  font-size: var(--fs-micro);
  line-height: 1.5;
}
</style>
