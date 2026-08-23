/**
 * Thin wrapper over an HTTP Range GET (docs/ui-spec.md §1.3 — the standing
 * 206 assertion this whole reader design is load-bearing on;
 * `scripts/check-range.mjs` is the automated check that the serving setup
 * honors it). Kept as one seam so the reader logic never touches `fetch`
 * headers directly.
 */

export interface RangeFetchResult {
  text: string;
  /** True if the server answered 206 with a Content-Range naming the full size. */
  partial: boolean;
  /** Total file size, from Content-Range's `/total` — undefined if unknown (e.g. plain 200). */
  totalBytes: number | undefined;
  status: number;
}

/**
 * GET `url` for byte range [start, end] (end is exclusive, half-open, to
 * match the reader's own bookkeeping) — omit `end` to mean "to EOF" (an
 * open-ended `bytes=start-` range, per RFC 7233). A 404 or network failure
 * is not swallowed here — schema §7's tolerance is about record *content*,
 * not about the transport failing outright; callers decide what "the run
 * disappeared mid-poll" means for their own state.
 */
export async function rangeFetch(
  url: string,
  start: number,
  end?: number,
): Promise<RangeFetchResult> {
  const rangeHeader = end === undefined ? `bytes=${start}-` : `bytes=${start}-${end - 1}`;
  const res = await fetch(url, { headers: { Range: rangeHeader } });
  const text = await res.text();
  const contentRange = res.headers.get("content-range");
  const totalBytes = contentRange
    ? (() => {
        const match = /\/(\d+)$/.exec(contentRange);
        return match ? Number(match[1]) : undefined;
      })()
    : undefined;
  return {
    text,
    partial: res.status === 206,
    totalBytes,
    status: res.status,
  };
}

/** Plain GET, no Range header — used for the small registry/sidecar-index JSON files. */
export async function fetchJson<T>(url: string): Promise<{ ok: true; body: T } | { ok: false; status: number }> {
  const res = await fetch(url);
  if (!res.ok) return { ok: false, status: res.status };
  const body = (await res.json()) as T;
  return { ok: true, body };
}
