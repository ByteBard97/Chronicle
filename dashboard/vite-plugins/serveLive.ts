import { createReadStream, existsSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { Connect, Plugin } from "vite";

/**
 * Serves ChronicleBridge's listener snapshot file
 * (adapters/skyrim/listener/whiterun-positions.json,
 * docs/design/chronicle-bridge-spatial-streamer.md's B4 "file-polling,
 * not a live server" decision) at /live/whiterun-positions.json --
 * `stores/livePositions.ts` polls this path.
 *
 * Unlike serveRuns.ts, no Range support: this is a single small
 * rolling snapshot the listener overwrites in place, not an
 * append-only growing log, so there is nothing to resume from a byte
 * offset. A 404 is the expected, normal state whenever no listener has
 * run yet -- next() falls through to Vite's usual handling rather than
 * treating a missing file as an error.
 *
 * Path is `CHRONICLE_LIVE_SNAPSHOT` if set, else the listener's own
 * default output path (adapters/skyrim/listener/whiterun-positions.json,
 * two levels above dashboard/).
 */
export function serveLive(): Plugin {
  const snapshotPath =
    process.env.CHRONICLE_LIVE_SNAPSHOT ??
    fileURLToPath(new URL("../../adapters/skyrim/listener/whiterun-positions.json", import.meta.url));

  const handler: Connect.NextHandleFunction = (req, res, next) => {
    if (req.url?.split(/[?#]/)[0] !== "/live/whiterun-positions.json") {
      next();
      return;
    }
    if (!existsSync(snapshotPath)) {
      next();
      return;
    }
    const stat = statSync(snapshotPath);
    if (stat.isDirectory()) {
      next();
      return;
    }
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Content-Length", stat.size);
    createReadStream(snapshotPath).pipe(res);
  };

  return {
    name: "chronicle-serve-live",
    configureServer(server) {
      server.middlewares.use(handler);
    },
    configurePreviewServer(server) {
      server.middlewares.use(handler);
    },
  };
}
