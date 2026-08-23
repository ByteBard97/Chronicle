import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveTailPoller, readByteRange } from "./streamReader";

afterEach(() => {
  vi.unstubAllGlobals();
});

/** A fake Range-serving endpoint over an in-memory string, growing on demand. */
function stubGrowingFile(initial: string) {
  let content = initial;
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
    const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
    const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
    const bytes = new TextEncoder().encode(content);
    let start = 0;
    let end = bytes.length;
    if (match) {
      start = Number(match[1]);
      end = match[2] === "" ? bytes.length : Number(match[2]) + 1;
    }
    end = Math.min(end, bytes.length);
    const slice = bytes.slice(start, end);
    const text = new TextDecoder().decode(slice);
    return new Response(text, {
      status: 206,
      headers: { "Content-Range": `bytes ${start}-${end - 1}/${bytes.length}` },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return {
    append(more: string) {
      content += more;
    },
  };
}

describe("readByteRange", () => {
  it("parses complete records in range and reports where the torn tail begins", async () => {
    stubGrowingFile('{"a":1}\n{"a":2}\n{"a":3');
    const result = await readByteRange("http://example/run/events.jsonl", 0);
    expect(result.records).toEqual([{ a: 1 }, { a: 2 }]);
    expect(result.consumedThrough).toBe('{"a":1}\n{"a":2}\n'.length);
  });
});

describe("LiveTailPoller", () => {
  it("picks up newly appended records on the next poll, from where the last one left off", async () => {
    const file = stubGrowingFile('{"tick":0}\n');
    const poller = new LiveTailPoller("http://example/run/events.jsonl", 0, 1000);

    const first = await poller.pollOnce();
    expect(first).toEqual([{ tick: 0 }]);
    expect(poller.position).toBe('{"tick":0}\n'.length);

    // Nothing new yet.
    const second = await poller.pollOnce();
    expect(second).toEqual([]);

    // The writer appends a new record.
    file.append('{"tick":1}\n');
    const third = await poller.pollOnce();
    expect(third).toEqual([{ tick: 1 }]);
  });

  it("never yields a torn record even if polled while a line is mid-write", async () => {
    const file = stubGrowingFile('{"tick":0}\n{"tick":1');
    const poller = new LiveTailPoller("http://example/run/events.jsonl", 0, 1000);

    const first = await poller.pollOnce();
    expect(first).toEqual([{ tick: 0 }]);

    // The second record is still being written (no trailing newline yet) --
    // must not appear.
    const second = await poller.pollOnce();
    expect(second).toEqual([]);

    file.append('}\n');
    const third = await poller.pollOnce();
    expect(third).toEqual([{ tick: 1 }]);
  });

  it("start() polls on the given interval and calls the listener only when new records arrive", async () => {
    vi.useFakeTimers();
    const file = stubGrowingFile('{"tick":0}\n');
    const poller = new LiveTailPoller("http://example/run/events.jsonl", 0, 1000);
    const onRecords = vi.fn();
    const stop = poller.start(onRecords);

    await vi.advanceTimersByTimeAsync(1000);
    expect(onRecords).toHaveBeenCalledTimes(1);
    expect(onRecords).toHaveBeenCalledWith([{ tick: 0 }], expect.any(Number));

    await vi.advanceTimersByTimeAsync(1000);
    // No new content -- listener not called again.
    expect(onRecords).toHaveBeenCalledTimes(1);

    file.append('{"tick":1}\n');
    await vi.advanceTimersByTimeAsync(1000);
    expect(onRecords).toHaveBeenCalledTimes(2);

    stop();
    vi.useRealTimers();
  });
});
