<script setup lang="ts">
/**
 * GlyphLegend — the "GLYPHS" legend row from map-c-skyrim.dc.html:
 * 111-117: the four worst-case glyph letters in their glyph colors with
 * their meaning, in precedence order (D ▸ G ▸ S ▸ N).
 */
const ITEMS = [
  { glyph: "D", label: "deviation" },
  { glyph: "G", label: "grudge" },
  { glyph: "S", label: "spreading" },
  { glyph: "N", label: "new belief" },
] as const;
</script>

<template>
  <div class="glyph-legend">
    <span class="glyph-legend__title">GLYPHS</span>
    <span v-for="item in ITEMS" :key="item.glyph" class="glyph-legend__item">
      <span
        class="glyph-legend__letter"
        :class="`glyph-legend__letter--${item.glyph}`"
        >{{ item.glyph }}</span
      >
      {{ item.label }}
    </span>
  </div>
</template>

<style scoped>
.glyph-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--c-text-dim);
}

.glyph-legend__title {
  font-family: var(--font-display);
  color: var(--c-panel-title);
  letter-spacing: 0.16em;
  flex: none;
  white-space: nowrap;
  font-size: 8px;
}

.glyph-legend__item {
  white-space: nowrap;
}

.glyph-legend__letter {
  font-weight: 600;
}

.glyph-legend__letter--D {
  color: var(--glyph-d);
}
.glyph-legend__letter--G {
  color: var(--glyph-g);
}
.glyph-legend__letter--S {
  color: var(--glyph-s);
}
.glyph-legend__letter--N {
  color: var(--glyph-n);
}
</style>
