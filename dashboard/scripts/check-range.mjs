#!/usr/bin/env node
// The standing Range assertion (ui-spec v1.2.1 §1.3 / build-plan M1
// acceptance): boots the dashboard's serving setup, fetches a run log with a
// `Range` header, and asserts 206. The one-time spike (see README.md
// "Range spike") verified the assumption manually once; this script is what
// catches it silently regressing later (a Vite upgrade, a proxy, a changed
// plugin order) — runnable standalone, in CI, and on checkout, with no
// server assumed to already be running.
//
// Usage:
//   node scripts/check-range.mjs           # checks `vite preview` (prod-like)
//   node scripts/check-range.mjs --dev      # checks `vite dev`
//   node scripts/check-range.mjs --both     # checks both, sequentially

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dashboardRoot = fileURLToPath(new URL("..", import.meta.url));
const repoRoot = path.resolve(dashboardRoot, "..");
const runsDir = process.env.CHRONICLE_RUNS_DIR ?? path.join(repoRoot, "runs");

function ensureFixtureRun() {
  const runDir = path.join(runsDir, "range-check-fixture");
  const logPath = path.join(runDir, "events.jsonl");
  if (!existsSync(logPath)) {
    mkdirSync(runDir, { recursive: true });
    const lines = [];
    for (let i = 0; i < 50; i++) {
      lines.push(
        JSON.stringify({
          schema_version: 1,
          seed_id: "range-check",
          save_uuid: "s0",
          generation: 0,
          tick: i,
          stream: "events",
          seq: i,
          payload: { kind: "noop", i },
        }),
      );
    }
    writeFileSync(logPath, lines.join("\n") + "\n");
  }
  return "range-check-fixture/events.jsonl";
}

async function waitForPort(port, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`http://localhost:${port}/`);
      await res.body?.cancel();
      return;
    } catch {
      await new Promise((r) => setTimeout(r, 150));
    }
  }
  throw new Error(`Timed out waiting for server on port ${port}`);
}

async function checkServer(mode) {
  const port = mode === "dev" ? 5183 : 4183;
  const args =
    mode === "dev" ? ["dev", "--port", String(port)] : ["preview", "--port", String(port)];

  const relLogPath = ensureFixtureRun();

  const child = spawn("node_modules/.bin/vite", args, {
    cwd: dashboardRoot,
    stdio: ["ignore", "pipe", "pipe"],
  });

  let stderr = "";
  child.stderr.on("data", (d) => (stderr += d.toString()));

  try {
    await waitForPort(port);

    const url = `http://localhost:${port}/runs/${relLogPath}`;
    const res = await fetch(url, { headers: { Range: "bytes=0-9" } });
    await res.body?.cancel();

    if (res.status !== 206) {
      throw new Error(
        `[${mode}] expected 206 for Range request to ${url}, got ${res.status}. ` +
          `This is the standing Range assertion (ui-spec §1.3) — if this fails, ` +
          `the reader design (byte-offset fetch, LIVE tailing) is not viable on ` +
          `the current serving setup. stderr:\n${stderr}`,
      );
    }
    const contentRange = res.headers.get("content-range");
    if (!contentRange) {
      throw new Error(`[${mode}] 206 response missing Content-Range header`);
    }
    console.log(`[${mode}] OK: 206 Partial Content, Content-Range: ${contentRange}`);
  } finally {
    child.kill();
  }
}

async function main() {
  const args = process.argv.slice(2);
  const modes = args.includes("--both")
    ? ["dev", "preview"]
    : args.includes("--dev")
      ? ["dev"]
      : ["preview"];

  for (const mode of modes) {
    await checkServer(mode);
  }
}

main().catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
