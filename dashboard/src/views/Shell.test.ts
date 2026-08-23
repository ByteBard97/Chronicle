import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import Shell from "./Shell.vue";

/**
 * `urlState.mount.test.ts` proves `useUrlState()` works when driven
 * directly. Nothing until now has actually mounted the app frame itself —
 * `vue-tsc`/`vite build` type-check and bundle components, they don't
 * execute them, so `v-model="urlState.run.value"` against RunPicker's
 * `defineModel` (the one non-obvious binding in the tree) had zero runtime
 * coverage. This does: mount Shell.vue for real, through a router and
 * Pinia, with fetch stubbed to 404 (runs/index.json's tolerated-absent
 * path per the work packet).
 */
describe("Shell.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function mountShell() {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(null, { status: 404 })),
    );
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: "/", component: Shell }],
    });
    await router.push("/");
    const wrapper = mount(Shell, {
      global: { plugins: [router, createPinia()] },
    });
    await router.isReady();
    await flushPromises();
    return wrapper;
  }

  it("boots without throwing and renders the empty view area", async () => {
    const wrapper = await mountShell();
    expect(wrapper.find("#empty-view-area").exists()).toBe(true);
  });

  it("shows the tolerated-absence message when runs/index.json 404s", async () => {
    const wrapper = await mountShell();
    expect(wrapper.text()).toContain("no runs/index.json yet");
  });

  it("renders the salience-level picker with the three ui-spec §2 defaults", async () => {
    const wrapper = await mountShell();
    const options = wrapper
      .findAll("#salience-level option")
      .map((o) => o.text());
    expect(options).toEqual(["developer", "observer", "story"]);
  });
});
