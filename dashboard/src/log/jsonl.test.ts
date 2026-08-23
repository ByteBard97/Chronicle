import { describe, expect, it } from "vitest";
import { JsonlTailReader, parseJsonlLines, splitCompleteLines } from "./jsonl";

describe("splitCompleteLines", () => {
  it("splits a fully newline-terminated chunk into all complete lines, empty remainder", () => {
    expect(splitCompleteLines('{"a":1}\n{"a":2}\n')).toEqual({
      lines: ['{"a":1}', '{"a":2}'],
      remainder: "",
    });
  });

  it("treats a non-terminated tail as the remainder, not a line (the torn-tail guard)", () => {
    // A tailing writer's growing log: the last record hasn't had its
    // newline flushed yet. docs/frame-log-schema.md §1: "a non-terminated
    // tail is not-yet-written — tailing a growing log must never yield a
    // torn record."
    expect(splitCompleteLines('{"a":1}\n{"a":2')).toEqual({
      lines: ['{"a":1}'],
      remainder: '{"a":2',
    });
  });

  it("an empty chunk splits to no lines and no remainder", () => {
    expect(splitCompleteLines("")).toEqual({ lines: [], remainder: "" });
  });
});

describe("parseJsonlLines", () => {
  it("parses each line as JSON and reports its byte length including the newline", () => {
    const result = parseJsonlLines(['{"a":1}', '{"a":2}']);
    expect(result.map((r) => r.record)).toEqual([{ a: 1 }, { a: 2 }]);
    expect(result[0]!.byteLength).toBe('{"a":1}'.length + 1);
  });

  it("skips a malformed line rather than throwing", () => {
    const result = parseJsonlLines(['{"a":1}', "not json", '{"a":2}']);
    expect(result.map((r) => r.record)).toEqual([{ a: 1 }, { a: 2 }]);
  });

  it("skips blank lines", () => {
    expect(parseJsonlLines(["", '{"a":1}', ""])).toHaveLength(1);
  });
});

describe("JsonlTailReader", () => {
  it("reassembles a record split across two feed() calls at a fetch boundary", () => {
    const reader = new JsonlTailReader();
    // Simulate a Range fetch that happened to cut mid-record.
    const firstBatch = reader.feed('{"a":1}\n{"a":2');
    expect(firstBatch.map((r) => r.record)).toEqual([{ a: 1 }]);

    const secondBatch = reader.feed('}\n{"a":3}\n');
    expect(secondBatch.map((r) => r.record)).toEqual([{ a: 2 }, { a: 3 }]);
  });

  it("advances consumedBytes only past complete records, never past a torn tail", () => {
    const reader = new JsonlTailReader();
    reader.feed('{"a":1}\n{"a":2');
    // '{"a":1}\n' is 8 bytes; the torn '{"a":2' remainder must not count.
    expect(reader.consumedBytes).toBe(8);
    reader.feed('}\n');
    expect(reader.consumedBytes).toBe(8 + '{"a":2}\n'.length);
  });

  it("starts consumedBytes at the given offset (resuming a poll from a known position)", () => {
    const reader = new JsonlTailReader(100);
    reader.feed('{"a":1}\n');
    expect(reader.consumedBytes).toBe(100 + '{"a":1}\n'.length);
  });

  it("never yields a torn record even when polled repeatedly before the writer finishes the line", () => {
    const reader = new JsonlTailReader();
    expect(reader.feed('{"a":1')).toEqual([]);
    expect(reader.feed("")).toEqual([]); // poll again, writer still hasn't flushed
    const batch = reader.feed('}\n');
    expect(batch.map((r) => r.record)).toEqual([{ a: 1 }]);
  });
});
