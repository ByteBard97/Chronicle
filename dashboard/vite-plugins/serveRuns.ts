import { createReadStream, statSync, existsSync, realpathSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";
import path from "node:path";
import type { Plugin, Connect } from "vite";

/**
 * The Range-spike fallback (docs/ui-spec.md §1.3 / dashboard-build-plan.md M1
 * task zero): `vite preview` serves only its build output directory and does
 * not honor `server.fs.allow`, so a request for the repo-root `runs/`
 * directory falls through to preview's SPA fallback (200 text/html) instead
 * of reaching the file at all — see dashboard/README.md's "Range spike"
 * section for the measured curl output.
 *
 * `vite dev` *does* serve `runs/` correctly today via a symlink
 * (`dashboard/runs -> ../runs`) plus `server.fs.allow`, using Vite's own
 * static middleware, which already answers 206 to Range requests. But
 * relying on two different code paths for dev and preview — Vite's built-in
 * static handling in one, nothing at all in the other — is exactly the kind
 * of asymmetry that regresses silently. This plugin replaces both with one
 * hand-rolled, Range-aware static file server for `/runs/*`, mounted in both
 * `configureServer` (dev) and `configurePreviewServer` (preview) hooks. It
 * is file-serving, not an application backend — ui-spec §1.3's permitted
 * fallback.
 *
 * Root directory is `CHRONICLE_RUNS_DIR` if set (shared env var per the
 * build plan §0), else `<repo-root>/runs` (one level above `dashboard/`).
 */
export function serveRuns(): Plugin {
  const runsRoot =
    process.env.CHRONICLE_RUNS_DIR ??
    fileURLToPath(new URL("../../runs", import.meta.url));

  const handler: Connect.NextHandleFunction = (req, res, next) => {
    if (!req.url || !req.url.startsWith("/runs/")) {
      next();
      return;
    }

    // Strip query/hash, then resolve under runsRoot with a path-traversal guard.
    let urlPath: string;
    try {
      urlPath = decodeURIComponent(req.url.split(/[?#]/)[0]!);
    } catch {
      res.statusCode = 400;
      res.end("Bad Request");
      return;
    }
    const relPath = urlPath.slice("/runs/".length);
    const filePath = path.join(runsRoot, relPath);

    if (!existsSync(filePath)) {
      next();
      return;
    }

    // Resolve symlinks before the boundary check, and require an exact root
    // match or a root-plus-separator prefix -- a plain startsWith on the
    // unresolved path allows both symlink escapes and sibling-directory
    // prefix collisions (e.g. runsRoot "/foo/runs" matching "/foo/runs-evil").
    const rootReal = realpathSync(path.resolve(runsRoot));
    let fileReal: string;
    try {
      fileReal = realpathSync(filePath);
    } catch {
      next();
      return;
    }
    if (fileReal !== rootReal && !fileReal.startsWith(rootReal + path.sep)) {
      res.statusCode = 403;
      res.end("Forbidden");
      return;
    }

    let stat;
    try {
      stat = statSync(fileReal);
    } catch {
      next();
      return;
    }
    if (stat.isDirectory()) {
      next();
      return;
    }

    const contentType = fileReal.endsWith(".json")
      ? "application/json"
      : fileReal.endsWith(".jsonl")
        ? "application/x-ndjson"
        : "application/octet-stream";

    res.setHeader("Accept-Ranges", "bytes");
    res.setHeader("Content-Type", contentType);
    res.setHeader("Cache-Control", "no-cache");

    const range = req.headers.range;
    if (!range) {
      res.statusCode = 200;
      res.setHeader("Content-Length", stat.size);
      createReadStream(fileReal).pipe(res);
      return;
    }

    const match = /^bytes=(\d*)-(\d*)$/.exec(range);
    if (!match) {
      res.statusCode = 416;
      res.setHeader("Content-Range", `bytes */${stat.size}`);
      res.end();
      return;
    }
    const [, startStr, endStr] = match;
    let start = startStr === "" ? undefined : Number(startStr);
    let end = endStr === "" ? undefined : Number(endStr);
    if (start === undefined && end !== undefined) {
      // suffix range: last `end` bytes
      start = Math.max(stat.size - end, 0);
      end = stat.size - 1;
    } else if (start !== undefined && end === undefined) {
      end = stat.size - 1;
    }
    if (
      start === undefined ||
      end === undefined ||
      start > end ||
      start >= stat.size
    ) {
      res.statusCode = 416;
      res.setHeader("Content-Range", `bytes */${stat.size}`);
      res.end();
      return;
    }
    end = Math.min(end, stat.size - 1);

    res.statusCode = 206;
    res.setHeader("Content-Range", `bytes ${start}-${end}/${stat.size}`);
    res.setHeader("Content-Length", end - start + 1);
    createReadStream(fileReal, { start, end }).pipe(res);
  };

  return {
    name: "chronicle-serve-runs",
    configureServer(server) {
      server.middlewares.use(handler);
    },
    configurePreviewServer(server) {
      server.middlewares.use(handler);
    },
  };
}
