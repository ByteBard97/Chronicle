<script setup lang="ts">
/**
 * ViewSwitcher — the app-wide nav idiom (lane 11 packet, Task 7, per the
 * pre-dispatch review's finding 1: no such idiom existed before this
 * lane — `/` and `/map` were disconnected islands). Three token-styled
 * links, active-view indicated, dropped into the right side of every
 * screen's 44px chrome strip (next to RunPicker/SalienceSwitch).
 * Established once here; retrofitted onto Shell.vue and MapScreen.vue,
 * installed fresh on FeedScreen.vue.
 *
 * Plain `<a href>` rather than `<router-link>`/`useRoute()` — deliberate:
 * `MapScreen.test.ts` mounts `MapScreen` with no router plugin installed
 * (only Pinia), and that test is out of bounds to edit. A component that
 * calls `useRoute()` throws with no injected router; this one takes the
 * active view as a prop instead, so it works identically whether or not a
 * router happens to be present in the test harness. The tradeoff (a full
 * navigation instead of client-side routing) is acceptable for a
 * top-level view switch — but a full navigation to a bare `/map`/`/feed`
 * would otherwise discard the current `run`/`t`/`sel`/`filters` (ui-spec
 * §1.2: the URL is the whole view state), so each link's `href` carries
 * `window.location.search` forward. `window.location` rather than
 * `useRoute()` for the same router-optionality reason above.
 */
export type ViewName = "console" | "map" | "feed";

defineProps<{ current: ViewName }>();

const currentSearch = typeof window !== "undefined" ? window.location.search : "";

const LINKS: { to: string; view: ViewName; label: string }[] = [
  { to: "/", view: "console", label: "console" },
  { to: "/map", view: "map", label: "map" },
  { to: "/feed", view: "feed", label: "feed" },
];
</script>

<template>
  <nav class="view-switcher" aria-label="view switcher">
    <a
      v-for="link in LINKS"
      :key="link.to"
      :href="`${link.to}${currentSearch}`"
      class="view-switcher__link"
      :class="{ 'view-switcher__link--active': current === link.view }"
      :aria-current="current === link.view ? 'page' : undefined"
    >
      {{ link.label }}
    </a>
  </nav>
</template>

<style scoped>
.view-switcher {
  display: flex;
  border: 1px solid var(--c-hairline);
  border-radius: var(--radius-chip);
  overflow: hidden;
  flex: none;
}

.view-switcher__link {
  appearance: none;
  border: none;
  border-left: 1px solid var(--c-hairline);
  background: transparent;
  color: var(--c-text-dim);
  font-family: var(--font-data);
  font-size: var(--fs-secondary);
  padding: 3px 10px;
  cursor: pointer;
  white-space: nowrap;
  text-decoration: none;
}

.view-switcher__link:hover {
  color: var(--c-text-body);
  text-decoration: none;
}

.view-switcher__link:first-child {
  border-left: none;
}

.view-switcher__link--active {
  background: var(--c-chip-active-fill);
  color: var(--c-accent-hover);
}
</style>
