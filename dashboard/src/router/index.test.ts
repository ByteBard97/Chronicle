import { describe, expect, it } from "vitest";
import { router } from "./index";

/**
 * `view=feed` (ui-spec §1.2's `view` query param) must actually land on
 * FeedScreen — lane 9's pytest `deep_link` fixture emits URLs shaped like
 * `/?run=...&view=feed&t=7&sel=...`, path `/`, view in the query. Without
 * the `beforeEach` guard in `./index.ts`, that URL renders Shell.vue with
 * an unread `view` param.
 */
describe("router: view=feed lands on /feed", () => {
  it("redirects a view=feed query to the /feed path, preserving the rest of the query", async () => {
    await router.push("/?run=whiterun-jarl-01&view=feed&t=7&sel=irileth");
    expect(router.currentRoute.value.path).toBe("/feed");
    expect(router.currentRoute.value.query.run).toBe("whiterun-jarl-01");
    expect(router.currentRoute.value.query.t).toBe("7");
    expect(router.currentRoute.value.query.sel).toBe("irileth");
  });

  it("redirects a view=map query to /map", async () => {
    await router.push("/?view=map");
    expect(router.currentRoute.value.path).toBe("/map");
  });

  it("leaves a URL with no view param alone", async () => {
    await router.push("/map?run=x");
    expect(router.currentRoute.value.path).toBe("/map");
  });

  it("does not loop when already at the target path for its view", async () => {
    await router.push("/feed?view=feed&run=x");
    expect(router.currentRoute.value.path).toBe("/feed");
    expect(router.currentRoute.value.query.run).toBe("x");
  });

  it("ignores an unknown view value rather than redirecting to nowhere", async () => {
    await router.push("/map?view=variant-tree");
    expect(router.currentRoute.value.path).toBe("/map");
  });

  it("redirects a view=scheddiff query to /scheddiff, preserving t and filters (lane 41)", async () => {
    await router.push('/?run=mourning-demo-01&view=scheddiff&t=50&filters={"npc":"sven"}');
    expect(router.currentRoute.value.path).toBe("/scheddiff");
    expect(router.currentRoute.value.query.run).toBe("mourning-demo-01");
    expect(router.currentRoute.value.query.t).toBe("50");
    expect(router.currentRoute.value.query.filters).toBe('{"npc":"sven"}');
  });
});
