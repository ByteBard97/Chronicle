import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import FeedFilterBar from "./FeedFilterBar.vue";
import type { FeedRow } from "../../log/feedReader";

/**
 * Lane 58 regression test (dossier T1.3 / nothing-salient developer-twin
 * finding): the outcome `<select>` used to render its dropdown *label*
 * with a hyphen (`rolled-against`) while its `value` -- and therefore the
 * URL-serialized `filters` param -- kept the underscore (`rolled_against`).
 * Typing the visibly-displayed label into a hand-constructed URL silently
 * matched nothing. Fixed (approach (a) from the work packet) by dropping
 * the cosmetic `.replace("_", "-")` transform so the label equals the
 * value exactly. This test locks that invariant down and proves a URL
 * built from the on-screen label round-trips to the right filter state.
 */
const rows: FeedRow[] = [];

function mountBar() {
  return mount(FeedFilterBar, { props: { rows, filters: {} } });
}

describe("FeedFilterBar outcome filter", () => {
  it("renders every outcome option's label identical to its value (no hyphen/underscore mismatch)", () => {
    const wrapper = mountBar();
    const outcomeSelect = wrapper.findAll("select")[2];
    const options = outcomeSelect.findAll("option").filter((o) => o.attributes("value") !== "");
    expect(options.length).toBeGreaterThan(0);
    for (const option of options) {
      expect(option.text()).toBe(option.attributes("value"));
    }
  });

  it("a URL-hand-typed value matching the visibly-displayed label selects the correct option and round-trips through emit", async () => {
    const wrapper = mountBar();
    const outcomeSelect = wrapper.findAll("select")[2];

    // What a user would hand-type into a URL after reading the dropdown's
    // on-screen label -- must equal the stored/emitted value.
    const displayedLabel = outcomeSelect
      .findAll("option")
      .find((o) => o.attributes("value") === "rolled_against")!
      .text();
    expect(displayedLabel).toBe("rolled_against");

    await outcomeSelect.setValue("rolled_against");
    const emitted = wrapper.emitted("update:filters");
    expect(emitted).toBeTruthy();
    expect(emitted![emitted!.length - 1][0]).toEqual({ outcome: "rolled_against" });
  });

  it("re-selecting a filter value the dropdown reports as selected matches the filters prop exactly (no unselected-looking mismatch)", () => {
    const wrapper = mount(FeedFilterBar, { props: { rows, filters: { outcome: "nothing_salient" } } });
    const outcomeSelect = wrapper.findAll("select")[2];
    expect((outcomeSelect.element as HTMLSelectElement).value).toBe("nothing_salient");
  });
});
