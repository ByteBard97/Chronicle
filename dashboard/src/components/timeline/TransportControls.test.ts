import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { mount, flushPromises } from "@vue/test-utils";
import TransportControls from "./TransportControls.vue";

/**
 * TransportControls.test.ts — lane 16 rewrite (authorized rewrite class:
 * the fixture-driven "visual parity only, no click handler" premise this
 * file asserted is exactly what this lane changes). `urlState.t` needs a
 * real router (`useRouteQuery`), so every test mounts against a
 * memory-history router and reads/writes `t` through it.
 */
async function mountAt(initialT: number | null, maxTick = 200) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div />" } }],
  });
  await router.push(initialT === null ? "/" : `/?t=${initialT}`);
  await router.isReady();
  const wrapper = mount(TransportControls, {
    props: { maxTick },
    global: { plugins: [router] },
  });
  await flushPromises();
  return { wrapper, router };
}

function tQuery(router: ReturnType<typeof createRouter>): string | undefined {
  const raw = router.currentRoute.value.query.t;
  return typeof raw === "string" ? raw : undefined;
}

describe("TransportControls", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the five transport buttons with their titles and the primary play button", () => {
    const wrapperPromise = mountAt(0);
    return wrapperPromise.then(({ wrapper }) => {
      expect(wrapper.find('[data-testid="transport-skip-back-day"]').attributes("title")).toBe("-1 day");
      expect(wrapper.find('[data-testid="transport-prev-day-boundary"]').attributes("title")).toBe("prev day boundary");
      expect(wrapper.find('[data-testid="transport-play-pause"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="transport-next-day-boundary"]').attributes("title")).toBe("next day boundary");
      expect(wrapper.find('[data-testid="transport-skip-forward-day"]').attributes("title")).toBe("+1 day");
    });
  });

  it("marks 1x active by default and switches the active speed on click", async () => {
    const { wrapper } = await mountAt(0);
    const speeds = wrapper.findAll(".transport__speed");
    expect(speeds.map((s) => s.text())).toEqual(["¼×", "1×", "4×", "8×"]);
    expect(speeds[1]!.classes()).toContain("transport__speed--active");
    await speeds[2]!.trigger("click");
    expect(speeds[2]!.classes()).toContain("transport__speed--active");
    expect(speeds[1]!.classes()).not.toContain("transport__speed--active");
  });

  it("+1 day / -1 day skip by exactly 24 ticks, relative to the current tick ('replace' mode -- no new history entry)", async () => {
    const { wrapper, router } = await mountAt(50);
    const historyLengthBefore = window.history.length;
    await wrapper.find('[data-testid="transport-skip-forward-day"]').trigger("click");
    await flushPromises();
    expect(tQuery(router)).toBe("74");
    await wrapper.find('[data-testid="transport-skip-back-day"]').trigger("click");
    await wrapper.find('[data-testid="transport-skip-back-day"]').trigger("click");
    await flushPromises();
    expect(tQuery(router)).toBe("26");
    // 'replace' mode: no history entries were pushed by these three writes.
    expect(window.history.length).toBe(historyLengthBefore);
  });

  it("day-boundary stepping snaps to the nearest 24-tick multiple, not a relative +/-24", async () => {
    const { wrapper, router } = await mountAt(30);
    await wrapper.find('[data-testid="transport-next-day-boundary"]').trigger("click");
    await flushPromises();
    expect(tQuery(router)).toBe("48"); // next multiple of 24 after 30
    await wrapper.find('[data-testid="transport-prev-day-boundary"]').trigger("click");
    await flushPromises();
    expect(tQuery(router)).toBe("24"); // previous multiple of 24 before 48
  });

  it("clamps writes to [0, maxTick]", async () => {
    const { wrapper, router } = await mountAt(5, 100);
    await wrapper.find('[data-testid="transport-skip-back-day"]').trigger("click");
    await flushPromises();
    expect(tQuery(router)).toBe("0");
  });

  it("play advances t at 1 tick/second for the 1x preset (fake timers)", async () => {
    vi.useFakeTimers();
    const { wrapper, router } = await mountAt(0);
    await wrapper.find('[data-testid="transport-play-pause"]').trigger("click");
    expect(wrapper.find('[data-testid="transport-play-pause"]').text()).toBe("⏸");
    await vi.advanceTimersByTimeAsync(1000);
    expect(tQuery(router)).toBe("1");
    await vi.advanceTimersByTimeAsync(3000);
    expect(tQuery(router)).toBe("4");
  });

  it("play advances 4 ticks/second at the 4x preset (shown as a multiplier, not a tick rate)", async () => {
    vi.useFakeTimers();
    const { wrapper, router } = await mountAt(0);
    await wrapper.findAll(".transport__speed")[2]!.trigger("click"); // 4x
    await wrapper.find('[data-testid="transport-play-pause"]').trigger("click");
    await vi.advanceTimersByTimeAsync(1000);
    expect(tQuery(router)).toBe("4");
  });

  it("play advances 1 tick per 4 seconds at the 1/4x preset", async () => {
    vi.useFakeTimers();
    const { wrapper, router } = await mountAt(0);
    await wrapper.findAll(".transport__speed")[0]!.trigger("click"); // 1/4x
    await wrapper.find('[data-testid="transport-play-pause"]').trigger("click");
    await vi.advanceTimersByTimeAsync(3999);
    expect(tQuery(router)).toBe("0");
    await vi.advanceTimersByTimeAsync(1);
    expect(tQuery(router)).toBe("1");
  });

  it("stops playback once the playhead reaches maxTick", async () => {
    vi.useFakeTimers();
    const { wrapper, router } = await mountAt(198, 200);
    await wrapper.find('[data-testid="transport-play-pause"]').trigger("click");
    await vi.advanceTimersByTimeAsync(5000);
    expect(tQuery(router)).toBe("200");
    expect(wrapper.find('[data-testid="transport-play-pause"]').text()).toBe("▶");
  });

  it("pauses when t changes for a reason other than this component's own play/step writes", async () => {
    vi.useFakeTimers();
    const { wrapper, router } = await mountAt(0);
    await wrapper.find('[data-testid="transport-play-pause"]').trigger("click");
    expect(wrapper.find('[data-testid="transport-play-pause"]').text()).toBe("⏸");
    // Simulate an external write (e.g. a marker click elsewhere in the bar).
    await router.push("/?t=99");
    await flushPromises();
    expect(wrapper.find('[data-testid="transport-play-pause"]').text()).toBe("▶");
    await vi.advanceTimersByTimeAsync(2000);
    expect(tQuery(router)).toBe("99"); // stayed put -- no longer playing
  });
});
