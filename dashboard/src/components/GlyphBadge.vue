<script setup lang="ts">
/**
 * GlyphBadge — the 12x12 letter badge for the worst-case glyph
 * precedence (ui-spec §2: deviation > grudge > spreading > new belief).
 * D11/D14/D15: DOM version for panels/legends; the map's per-marker
 * glyph is a canvas draw, out of scope here.
 */
export type Glyph = "D" | "G" | "S" | "N";

defineProps<{ glyph: Glyph }>();
</script>

<script lang="ts">
export const GLYPH_LABELS: Record<Glyph, string> = {
  D: "deviation",
  G: "grudge",
  S: "spreading",
  N: "new belief",
};
</script>

<template>
  <span class="glyph-badge" :class="`glyph-badge--${glyph}`">{{ glyph }}</span>
</template>

<style scoped>
.glyph-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: var(--glyph-badge-size);
  height: var(--glyph-badge-size);
  font-size: var(--glyph-badge-font);
  font-weight: 600;
  border-radius: 2px;
  background: rgba(8, 10, 13, 0.9);
  border: var(--glyph-badge-border-width) solid currentColor;
  flex: none;
}

.glyph-badge--D {
  color: var(--glyph-d);
}
.glyph-badge--G {
  color: var(--glyph-g);
}
.glyph-badge--S {
  color: var(--glyph-s);
}
.glyph-badge--N {
  color: var(--glyph-n);
}
</style>
