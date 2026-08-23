import { createRouter, createWebHistory } from "vue-router";
import Shell from "../views/Shell.vue";
import MapScreen from "../views/MapScreen.vue";
import FeedScreen from "../views/FeedScreen.vue";
import VariantTreeScreen from "../views/VariantTreeScreen.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "shell", component: Shell },
    { path: "/map", name: "map", component: MapScreen },
    { path: "/feed", name: "feed", component: FeedScreen },
    { path: "/tree", name: "tree", component: VariantTreeScreen },
  ],
});

/**
 * `urlState.view` (ui-spec §1.2) is a query param, not a path — a deep
 * link like `/?run=...&view=feed&t=7` (lane 9's pytest `deep_link`
 * fixture emits exactly this shape) names the intended view in the query
 * string while sitting at path `/`. Routes above are path-addressed, so
 * without this, `view=feed` never actually lands on FeedScreen — it
 * renders Shell.vue with an unread `view` param. This guard maps the
 * known `view` values onto their paths, preserving the rest of the query
 * (`run`/`t`/`sel`/`filters`/...) so nothing else in the URL is lost.
 *
 * Guarded by `target !== to.path` so a URL that's already at the right
 * path for its `view` (or has no/unknown `view`) does not loop or
 * redirect unnecessarily.
 */
const VIEW_PATHS: Record<string, string> = {
  console: "/",
  shell: "/",
  map: "/map",
  feed: "/feed",
  tree: "/tree",
};

router.beforeEach((to) => {
  const view = typeof to.query.view === "string" ? to.query.view : undefined;
  if (view === undefined) return true;
  const target = VIEW_PATHS[view];
  if (target === undefined || target === to.path) return true;
  return { path: target, query: to.query, hash: to.hash };
});
