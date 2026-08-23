<script setup lang="ts">
/**
 * PanelGlass — the frosted-glass DOM panel chrome from design-tokens.md
 * ("panel glass: rgba(10,12,14,.82) + backdrop-filter: blur(10px) — DOM
 * panels only, never per-marker"). Every floating/docked panel (lens
 * legend, layer toggles, zoom control, NPC inspector, timeline footer)
 * is this shell with a tone variant, per the alpha differences actually
 * present in map-c-skyrim.dc.html (top bar .9, inspector/footer .92,
 * legend/zoom .85 — see tokens.css's EXTENDED section).
 */
export type PanelTone = "default" | "topbar" | "strong" | "soft" | "inspector";

withDefaults(
  defineProps<{
    tone?: PanelTone;
    /** Panel corner radius follows --radius-panel; chips/pills opt out. */
    padded?: boolean;
  }>(),
  { tone: "default", padded: true },
);
</script>

<template>
  <div
    class="panel-glass"
    :class="[`panel-glass--${tone}`, { 'panel-glass--padded': padded }]"
  >
    <slot />
  </div>
</template>

<style scoped>
.panel-glass {
  background: var(--c-panel-glass);
  backdrop-filter: blur(10px);
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-panel);
}

.panel-glass--padded {
  padding: var(--panel-padding) 11px;
}

.panel-glass--topbar {
  background: var(--c-panel-glass-topbar);
}

.panel-glass--strong {
  background: var(--c-panel-glass-strong);
}

.panel-glass--soft {
  background: var(--c-panel-glass-soft);
  border-color: var(--c-hairline-soft);
}

.panel-glass--inspector {
  background: var(--c-panel-glass-inspector);
}
</style>
