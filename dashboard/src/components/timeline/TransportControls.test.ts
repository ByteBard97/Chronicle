import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import TransportControls from "./TransportControls.vue";

describe("TransportControls", () => {
  it("renders the five transport buttons with their glyphs and titles, primary marked on ▶", () => {
    const wrapper = mount(TransportControls);
    const buttons = wrapper.findAll(".transport__btn");
    expect(buttons.map((b) => b.text())).toEqual([
      "◀◀D",
      "◀|",
      "▶",
      "|▶",
      "D▶▶",
    ]);
    expect(buttons.map((b) => b.attributes("title"))).toEqual([
      "-1 day",
      "prev block",
      undefined,
      "next block",
      "+1 day",
    ]);
    expect(buttons[2]!.classes()).toContain("transport__btn--primary");
  });

  it("marks 1x active by default and swaps the active speed with a prop", () => {
    const wrapper = mount(TransportControls);
    const speeds = wrapper.findAll(".transport__speed");
    expect(speeds.map((s) => s.text())).toEqual(["¼×", "1×", "4×", "8×"]);
    const active = speeds.filter((s) =>
      s.classes().includes("transport__speed--active"),
    );
    expect(active).toHaveLength(1);
    expect(active[0]!.text()).toBe("1×");
  });

  it("marks a different speed active when activeSpeed is set", () => {
    const wrapper = mount(TransportControls, { props: { activeSpeed: "4×" } });
    const speeds = wrapper.findAll(".transport__speed");
    const active = speeds.filter((s) =>
      s.classes().includes("transport__speed--active"),
    );
    expect(active).toHaveLength(1);
    expect(active[0]!.text()).toBe("4×");
  });

  it("has no click handler wired yet: clicking a button changes nothing rendered", async () => {
    const wrapper = mount(TransportControls);
    const btn = wrapper.findAll(".transport__btn")[2]!;
    const before = wrapper.html();
    // No @click handler is declared in the template (playback wiring
    // lands with the frame-log lane per the docstring); asserting on
    // VTU's emitted() doesn't work here since it also records raw
    // native listener invocations (see NpcMarker/ZoomControls tests'
    // defaultPrevented checks) — the real invariant for a decorative
    // control is that the rendered output doesn't change.
    await btn.trigger("click");
    expect(wrapper.html()).toBe(before);
  });
});
