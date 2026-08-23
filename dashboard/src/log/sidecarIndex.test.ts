import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchSidecarIndex, keyframeAtOrBefore, tickAtOrBefore } from "./sidecarIndex";
import type { SidecarStreamIndex } from "./types";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchSidecarIndex", () => {
  it("reports 'missing' on 404 -- pure acceleration, absence just means 'scan from byte 0'", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(null, { status: 404 })));
    const result = await fetchSidecarIndex("run-a");
    expect(result.status).toBe("missing");
    expect(result.index.streams.events.tick_offsets).toEqual({});
  });

  it("loads a well-formed sidecar index", async () => {
    const body = {
      schema_version: 1,
      streams: {
        events: { tick_offsets: { "0": 0, "24": 970 }, keyframe_offsets: [{ tick: 24, offset: 970 }] },
        trace: { tick_offsets: { "0": 0, "1": 392 } },
      },
    };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })));
    const result = await fetchSidecarIndex("run-a");
    expect(result.status).toBe("loaded");
    expect(result.index.streams.events.tick_offsets["24"]).toBe(970);
  });

  it("degrades a malformed sidecar (missing streams) to 'malformed' with empty fallback indexes", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ oops: true }), { status: 200 })));
    const result = await fetchSidecarIndex("run-a");
    expect(result.status).toBe("malformed");
    expect(result.index.streams.trace.tick_offsets).toEqual({});
  });
});

describe("tickAtOrBefore", () => {
  const streamIndex: SidecarStreamIndex = { tick_offsets: { "0": 0, "10": 100, "24": 970 } };

  it("finds the largest known tick <= t", () => {
    expect(tickAtOrBefore(streamIndex, 15)).toBe(10);
    expect(tickAtOrBefore(streamIndex, 24)).toBe(24);
    expect(tickAtOrBefore(streamIndex, 1000)).toBe(24);
  });

  it("returns null when t is before every known tick", () => {
    expect(tickAtOrBefore({ tick_offsets: { "5": 50 } }, 4)).toBeNull();
  });
});

describe("keyframeAtOrBefore", () => {
  const streamIndex: SidecarStreamIndex = {
    tick_offsets: {},
    keyframe_offsets: [{ tick: 24, offset: 970 }, { tick: 48, offset: 2000 }],
  };

  it("finds the latest keyframe at or before T", () => {
    expect(keyframeAtOrBefore(streamIndex, 30)).toEqual({ tick: 24, offset: 970 });
    expect(keyframeAtOrBefore(streamIndex, 48)).toEqual({ tick: 48, offset: 2000 });
  });

  it("returns null when no keyframe exists at or before T", () => {
    expect(keyframeAtOrBefore(streamIndex, 10)).toBeNull();
  });
});
