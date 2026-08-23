import { describe, expect, it } from "vitest";
import {
  URL_STATE_DEFAULTS,
  decodeUrlState,
  encodeUrlState,
  type UrlState,
} from "./urlState";

function roundTrip(state: UrlState): UrlState {
  return decodeUrlState(encodeUrlState(state));
}

describe("urlState codec: state -> URL -> state is identity", () => {
  it("round-trips the all-defaults state to an empty query", () => {
    const query = encodeUrlState(URL_STATE_DEFAULTS as UrlState);
    expect(query).toEqual({});
    expect(roundTrip(URL_STATE_DEFAULTS as UrlState)).toEqual(
      URL_STATE_DEFAULTS,
    );
  });

  it("round-trips a fully populated state", () => {
    const state: UrlState = {
      run: "run-042",
      branch: "3f9c.2",
      t: 4183,
      view: "map",
      sel: ["npc-1", "npc-2"],
      panels: ["inspector:npc-1"],
      filters: { salience: "story", npc: "npc-1" },
      runB: "run-041",
      alignment: "tick",
    };
    expect(roundTrip(state)).toEqual(state);
  });

  it("round-trips t=0 (falsy but not absent)", () => {
    const state: UrlState = { ...URL_STATE_DEFAULTS, t: 0 };
    const query = encodeUrlState(state);
    expect(query.t).toBe("0");
    expect(roundTrip(state)).toEqual(state);
  });

  it("empty collections encode to absent, and absent decodes back to empty", () => {
    const state: UrlState = {
      ...URL_STATE_DEFAULTS,
      sel: [],
      panels: [],
      filters: {},
    };
    const query = encodeUrlState(state);
    expect(query.sel).toBeUndefined();
    expect(query.panels).toBeUndefined();
    expect(query.filters).toBeUndefined();
    expect(decodeUrlState({})).toEqual(URL_STATE_DEFAULTS);
  });

  it("preserves values containing the delimiter character (comma) in array fields", () => {
    const state: UrlState = {
      ...URL_STATE_DEFAULTS,
      sel: ["npc,with,commas", "npc-2"],
    };
    expect(roundTrip(state)).toEqual(state);
  });

  it("decodes malformed filters JSON to the empty-object default rather than throwing", () => {
    expect(decodeUrlState({ filters: "{not json" })).toEqual(
      URL_STATE_DEFAULTS,
    );
  });

  it("decodes a non-object filters JSON value to the empty-object default", () => {
    expect(decodeUrlState({ filters: "[1,2,3]" })).toEqual(URL_STATE_DEFAULTS);
  });

  it("decodes an empty-string t to null, not NaN or 0", () => {
    expect(decodeUrlState({ t: "" })).toEqual(URL_STATE_DEFAULTS);
  });

  it("decodes a non-numeric t to null", () => {
    expect(decodeUrlState({ t: "not-a-number" })).toEqual(URL_STATE_DEFAULTS);
  });

  it("decodes a fractional or negative t to null (ticks are non-negative integers)", () => {
    expect(decodeUrlState({ t: "12.5" })).toEqual(URL_STATE_DEFAULTS);
    expect(decodeUrlState({ t: "-5" })).toEqual(URL_STATE_DEFAULTS);
  });

  // vue-router's LocationQuery hands decoders three shapes a hand-built
  // UrlStateQuery in the tests above never exercises: `null` for a bare key
  // (`?sel`), and `string[]` for a repeated key (`?t=1&t=2`). A decoder that
  // only compiles against `string | undefined` can still crash or silently
  // misparse on these at runtime -- these cases are the regression test for
  // that class of bug (a bare `?t` must never decode as `t: 0`).
  describe("raw shapes vue-router can hand a decoder beyond a plain string", () => {
    it("treats a bare key (null) as absent, not as a value to parse", () => {
      expect(decodeUrlState({ run: null })).toEqual(URL_STATE_DEFAULTS);
      expect(decodeUrlState({ t: null })).toEqual(URL_STATE_DEFAULTS);
      expect(decodeUrlState({ sel: null })).toEqual(URL_STATE_DEFAULTS);
      expect(decodeUrlState({ filters: null })).toEqual(URL_STATE_DEFAULTS);
    });

    it("takes the first value of a repeated key rather than throwing", () => {
      expect(decodeUrlState({ run: ["run-a", "run-b"] })).toEqual({
        ...URL_STATE_DEFAULTS,
        run: "run-a",
      });
      expect(decodeUrlState({ t: ["3", "4"] })).toEqual({
        ...URL_STATE_DEFAULTS,
        t: 3,
      });
      expect(decodeUrlState({ sel: ["a,b", "c"] })).toEqual({
        ...URL_STATE_DEFAULTS,
        sel: ["a", "b"],
      });
    });

    it("treats an empty repeated-key array as absent", () => {
      expect(decodeUrlState({ run: [] })).toEqual(URL_STATE_DEFAULTS);
    });
  });
});
