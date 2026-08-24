import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import InjectionConsole from "./InjectionConsole.vue";

// Lane 46: the console must display the CLI's *real* writing invocation
// (chronicle/cli.py's `_inject_write`: run_id positional, `--event
// '<json>'`), not just the compose-only form lane 9 built. Exact
// string match, following lane 9's precedent of matching flags exactly
// rather than a loose "contains inject" check.
describe("InjectionConsole (lane 46: writing-form CLI invocation)", () => {
  it("displays the compose-only invocation unchanged (lane 9's form)", () => {
    const wrapper = mount(InjectionConsole);
    const pres = wrapper.findAll(".injection-console__code--cli");
    expect(pres[0].text()).toBe(
      "chronicle inject --run t6-jarl-01 --at 31442 --type npc_died --payload '{ \"text\": \"\" }'",
    );
  });

  it("displays the real writing invocation with positional run_id and --event JSON", () => {
    const wrapper = mount(InjectionConsole);
    const eventJson = wrapper.find(".injection-console__preview .injection-console__code").text();
    const pres = wrapper.findAll(".injection-console__code--cli");
    const writeInvocation = pres[1].text();

    expect(writeInvocation).toBe(`chronicle inject t6-jarl-01 --event '${eventJson}'`);
    // Sanity: the reused JSON really is the same object the preview shows.
    expect(JSON.parse(eventJson)).toEqual({
      event_type: "npc_died",
      run_id: "t6-jarl-01",
      at_tick: 31442,
      actor: null,
      payload: { text: "" },
    });
  });

  it("shows a LIVE-only / historical-tick-refusal note next to the writing invocation", () => {
    const wrapper = mount(InjectionConsole);
    expect(wrapper.find(".injection-console__write-note").text()).toContain("LIVE only");
    expect(wrapper.find(".injection-console__write-note").text()).toContain("fork");
  });

  it("updates the writing invocation to reflect edited run/type/actor/payload", async () => {
    const wrapper = mount(InjectionConsole);
    await wrapper.find("input[type=text]").setValue("other-run");
    await wrapper.find("select").setValue("crime_witnessed");

    const pres = wrapper.findAll(".injection-console__code--cli");
    const writeInvocation = pres[1].text();
    expect(writeInvocation.startsWith("chronicle inject other-run --event '")).toBe(true);
    expect(writeInvocation).toContain('"event_type": "crime_witnessed"');
  });
});
