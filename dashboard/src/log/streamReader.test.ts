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

/**
 * A fake endpoint that behaves like the real dev/preview static-file
 * server against a STATIC (non-growing) file: any `bytes=N-` request
 * where `N` is at or past the file's current length gets a real 416
 * (lane 15 Task 3 -- the bug this simulates: a poller sitting exactly at
 * EOF re-requesting `bytes=<EOF>-` forever).
 */
function stubStaticFileWith416(content: string) {
  const bytes = new TextEncoder().encode(content);
  const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
    const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
    const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
    const start = match ? Number(match[1]) : 0;
    if (start >= bytes.length) {
      return new Response(null, { status: 416 });
    }
    const end = match && match[2] !== "" ? Math.min(Number(match[2]) + 1, bytes.length) : bytes.length;
    const text = new TextDecoder().decode(bytes.slice(start, end));
    return new Response(text, {
      status: 206,
      headers: { "Content-Range": `bytes ${start}-${end - 1}/${bytes.length}` },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
}

describe("readByteRange", () => {
  it("parses complete records in range and reports where the torn tail begins", async () => {
    stubGrowingFile('{"a":1}\n{"a":2}\n{"a":3');
    const result = await readByteRange("http://example/run/events.jsonl", 0);
    expect(result.records).toEqual([{ a: 1 }, { a: 2 }]);
    expect(result.consumedThrough).toBe('{"a":1}\n{"a":2}\n'.length);
  });

  it("surfaces the transport's raw status (lane 15: LiveTailPoller needs the 416/206 distinction)", async () => {
    stubStaticFileWith416('{"a":1}\n');
    const result = await readByteRange("http://example/run/events.jsonl", 0);
    expect(result.status).toBe(206);

    const atEof = await readByteRange("http://example/run/events.jsonl", '{"a":1}\n'.length);
    expect(atEof.status).toBe(416);
    expect(atEof.records).toEqual([]);
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

  describe("416 backoff (lane 15 Task 3)", () => {
    it("start() backs off on sustained 416s (delay grows, observed via the actual schedule)", async () => {
      vi.useFakeTimers();
      stubStaticFileWith416('{"tick":0}\n');
      // Start already at EOF -- every poll is a 416 until we append.
      const poller = new LiveTailPoller("http://example/run/events.jsonl", '{"tick":0}\n'.length, 1000);
      const onRecords = vi.fn();
      const pollSpy = vi.spyOn(poller, "pollOnce");
      poller.start(onRecords);

      // Poll 1 at t=1000 (base interval): 416, backs off to 2000.
      await vi.advanceTimersByTimeAsync(1000);
      expect(pollSpy).toHaveBeenCalledTimes(1);

      // Next poll should be scheduled 2000ms later, not 1000ms -- confirm
      // nothing fires at the old base interval.
      await vi.advanceTimersByTimeAsync(1000);
      expect(pollSpy).toHaveBeenCalledTimes(1);
      await vi.advanceTimersByTimeAsync(1000);
      expect(pollSpy).toHaveBeenCalledTimes(2); // fires at cumulative 2000ms after poll 1

      // Poll 2 also 416s -> backs off to 4000. Confirm the gap grew again.
      await vi.advanceTimersByTimeAsync(3000);
      expect(pollSpy).toHaveBeenCalledTimes(2);
      await vi.advanceTimersByTimeAsync(1000);
      expect(pollSpy).toHaveBeenCalledTimes(3); // fires at cumulative 4000ms after poll 2

      vi.useRealTimers();
      poller.stop();
    });

    it("resets to the base interval as soon as a read makes real progress", async () => {
      vi.useFakeTimers();
      const initial = '{"tick":0}\n';
      const file = { content: initial };
      const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
        const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
        const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
        const bytes = new TextEncoder().encode(file.content);
        const start = match ? Number(match[1]) : 0;
        if (start >= bytes.length) return new Response(null, { status: 416 });
        const text = new TextDecoder().decode(bytes.slice(start));
        return new Response(text, {
          status: 206,
          headers: { "Content-Range": `bytes ${start}-${bytes.length - 1}/${bytes.length}` },
        });
      });
      vi.stubGlobal("fetch", fetchMock);

      const poller = new LiveTailPoller("http://example/run/events.jsonl", initial.length, 1000);
      const onRecords = vi.fn();
      const pollSpy = vi.spyOn(poller, "pollOnce");
      poller.start(onRecords);

      // Two 416s -> backed off to 4000ms before the next poll.
      await vi.advanceTimersByTimeAsync(1000);
      await vi.advanceTimersByTimeAsync(2000);
      expect(pollSpy).toHaveBeenCalledTimes(2);

      // New data lands. The poller is still waiting out its 4000ms
      // backoff window -- append now, then let that poll fire and see it
      // reset back to the 1000ms base for the *next* schedule.
      file.content += '{"tick":1}\n';
      await vi.advanceTimersByTimeAsync(4000);
      expect(pollSpy).toHaveBeenCalledTimes(3);
      expect(onRecords).toHaveBeenCalledWith([{ tick: 1 }], expect.any(Number));

      // Next poll should now be back at the 1000ms base, not another
      // backed-off wait.
      await vi.advanceTimersByTimeAsync(1000);
      expect(pollSpy).toHaveBeenCalledTimes(4);

      vi.useRealTimers();
      poller.stop();
    });

    it("caps the backoff at 10s no matter how many consecutive 416s occur", async () => {
      vi.useFakeTimers();
      stubStaticFileWith416('{"tick":0}\n');
      const poller = new LiveTailPoller("http://example/run/events.jsonl", '{"tick":0}\n'.length, 1000);
      const pollSpy = vi.spyOn(poller, "pollOnce");
      poller.start(vi.fn());

      // 1000 -> 2000 -> 4000 -> 8000 -> 10000 (would be 16000, capped) -> 10000 (stays capped).
      const expectedGaps = [1000, 2000, 4000, 8000, 10000, 10000];
      for (let i = 0; i < expectedGaps.length; i++) {
        await vi.advanceTimersByTimeAsync(expectedGaps[i]!);
        expect(pollSpy).toHaveBeenCalledTimes(i + 1);
      }

      vi.useRealTimers();
      poller.stop();
    });
  });
});
