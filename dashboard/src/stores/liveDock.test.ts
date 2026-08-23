import { describe, expect, it, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useLiveDockStore } from "./liveDock";

describe("liveDock store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("starts docked, following newest frame", () => {
    const store = useLiveDockStore();
    expect(store.docked).toBe(true);
    expect(store.statusText).toBe("LIVE — docked · following newest frame · +0 events · scrub to detach");
  });

  it("detach() switches to detached and resets the count", () => {
    const store = useLiveDockStore();
    store.recordNewEvents(3);
    store.detach();
    expect(store.docked).toBe(false);
    expect(store.newEventCount).toBe(0);
  });

  it("counts new events while detached, reflected in statusText", () => {
    const store = useLiveDockStore();
    store.detach();
    store.recordNewEvents(2);
    store.recordNewEvents(1);
    expect(store.newEventCount).toBe(3);
    expect(store.statusText).toContain("+3 events since detaching");
  });

  it("dock() resumes following and clears the pending count", () => {
    const store = useLiveDockStore();
    store.detach();
    store.recordNewEvents(5);
    store.dock();
    expect(store.docked).toBe(true);
    expect(store.newEventCount).toBe(0);
  });
});
