#!/usr/bin/env node
// Visual parity harness: screenshots the Vue app and the approved mockup
// (design/map-c-skyrim.dc.html, rendered by its custom runtime via
// design/support.js) side by side at 1600×900 and diffs them with
// pixelmatch. Writes scripts/visual-diff-output/{vue,mock,diff}.png and
// prints an overall diff percentage plus per-region notes.
//
// Servers: by default this script builds `dist/` if missing, boots
// `vite preview` for the Vue app, and serves `design/` over a tiny inline
// static file server. Pass --vue-url/--mock-url to point at already-running
// servers instead (then no server is started for that side).
//
// Usage:
//   node scripts/visual-diff.mjs [--vue-url URL] [--mock-url URL] [--out DIR]
//   npm run visual-diff

import { spawn } from "node:child_process";
import { createServer } from "node:http";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  statSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const dashboardRoot = fileURLToPath(new URL("..", import.meta.url));
const designDir = path.join(dashboardRoot, "design");

const VIEWPORT = { width: 1600, height: 900 };
const DEFAULT_VUE_PORT = 4173;
const DEFAULT_MOCK_PORT = 4815;
const NAV_TIMEOUT_MS = 60_000;
const SERVER_TIMEOUT_MS = 30_000;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".webp": "image/webp",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".md": "text/markdown; charset=utf-8",
};

function parseArgs(argv) {
  const opts = {
    vueUrl: null,
    mockUrl: null,
    out: path.join(dashboardRoot, "scripts", "visual-diff-output"),
  };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--vue-url") opts.vueUrl = argv[++i];
    else if (argv[i] === "--mock-url") opts.mockUrl = argv[++i];
    else if (argv[i] === "--out") opts.out = path.resolve(argv[++i]);
    else if (argv[i] === "--help" || argv[i] === "-h") {
      console.log(
        "Usage: node scripts/visual-diff.mjs [--vue-url URL] [--mock-url URL] [--out DIR]",
      );
      process.exit(0);
    } else {
      console.error(`unknown argument: ${argv[i]}`);
      process.exit(2);
    }
  }
  opts.vueUrl ??= `http://127.0.0.1:${DEFAULT_VUE_PORT}/`;
  opts.mockUrl ??= `http://127.0.0.1:${DEFAULT_MOCK_PORT}/map-c-skyrim.dc.html`;
  return opts;
}

/** Poll until the URL answers, or give up. */
async function waitForServer(url, label) {
  const deadline = Date.now() + SERVER_TIMEOUT_MS;
  let lastErr = "";
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { method: "HEAD" });
      if (res.ok || res.status === 404) return; // 404 still means "up"
      lastErr = `HTTP ${res.status}`;
    } catch (err) {
      lastErr = err.message;
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`${label} server did not come up at ${url}: ${lastErr}`);
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: dashboardRoot,
      stdio: "inherit",
      ...opts,
    });
    child.on("exit", (code) =>
      code === 0
        ? resolve()
        : reject(new Error(`${cmd} ${args.join(" ")} exited ${code}`)),
    );
  });
}

/**
 * Bind a server on `preferred` port, falling back to an ephemeral one if
 * it's taken (other lanes run servers in this tree). Returns the actual port.
 */
function listenOnFreePort(server, preferred) {
  return new Promise((resolve, reject) => {
    server.once("error", (err) => {
      if (err.code === "EADDRINUSE" && preferred !== 0) {
        server.listen(0, () => resolve(server.address().port));
      } else {
        reject(err);
      }
    });
    // No host: dual-stack bind so a conflict on either [::1] or 127.0.0.1
    // (other lanes' servers) is detected.
    server.listen(preferred, () => resolve(server.address().port));
  });
}

/** Minimal static file server for design/ (mockup + support.js + assets). */
function serveStatic(rootDir, preferredPort) {
  const server = createServer((req, res) => {
    const urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
    const rel = urlPath === "/" ? "/map-c-skyrim.dc.html" : urlPath;
    const file = path.normalize(path.join(rootDir, rel));
    if (!file.startsWith(rootDir) || !existsSync(file) || !statSync(file).isFile()) {
      res.writeHead(404).end("not found");
      return;
    }
    res.writeHead(200, {
      "content-type": MIME[path.extname(file)] ?? "application/octet-stream",
    });
    res.end(readFileSync(file));
  });
  return listenOnFreePort(server, preferredPort).then((port) => ({
    server,
    port,
  }));
}

async function screenshot(browser, url, file) {
  const page = await browser.newPage({ viewport: VIEWPORT });
  try {
    // The mockup pulls fonts/React from CDNs; networkidle can stall on
    // flaky networks, so fall back to a plain load + settle wait.
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: NAV_TIMEOUT_MS });
    } catch {
      await page.goto(url, { waitUntil: "load", timeout: NAV_TIMEOUT_MS });
      await page.waitForTimeout(3000);
    }
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(500); // let the custom runtime finish rendering
    await page.screenshot({ path: file });
  } finally {
    await page.close();
  }
}

/** Diff % per named horizontal band of the 1600×900 shot. */
function regionNotes(imgA, imgB) {
  const regions = [
    ["top bar (y 0–44)", 0, 44],
    ["main pane (y 44–802)", 44, 802],
    ["timeline strip (y 802–900)", 802, 900],
  ];
  const notes = [];
  for (const [name, y0, y1] of regions) {
    let diff = 0;
    let total = 0;
    for (let y = y0; y < y1; y++) {
      for (let x = 0; x < imgA.width; x++) {
        const i = (y * imgA.width + x) * 4;
        const d =
          Math.abs(imgA.data[i] - imgB.data[i]) +
          Math.abs(imgA.data[i + 1] - imgB.data[i + 1]) +
          Math.abs(imgA.data[i + 2] - imgB.data[i + 2]);
        total++;
        if (d > 30) diff++;
      }
    }
    notes.push(`  ${name}: ${((diff / total) * 100).toFixed(1)}% pixels differ`);
  }
  return notes;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  mkdirSync(opts.out, { recursive: true });

  const cleanup = [];
  try {
    // --- Vue side -----------------------------------------------------
    const managingVue = !process.argv.includes("--vue-url");
    if (managingVue) {
      if (!existsSync(path.join(dashboardRoot, "dist", "index.html"))) {
        console.log("[visual-diff] dist/ missing — building first…");
        await run("npm", ["run", "build"]);
      }
      // Probe for a free port first — other lanes run servers in this tree.
      // (Close the probe before vite binds it; the race window is tiny.)
      const probe = createServer();
      const port = await listenOnFreePort(probe, DEFAULT_VUE_PORT);
      await new Promise((r) => probe.close(r));
      console.log(`[visual-diff] starting vite preview on :${port}`);
      // --host 127.0.0.1: vite's default "localhost" resolves to [::1] on
      // this box, which the IPv4 waitForServer poll below would never see.
      // detached + group kill: npx wraps vite in a grandchild, so killing
      // only the direct child orphans the actual server.
      const preview = spawn(
        "npx",
        [
          "vite",
          "preview",
          "--host",
          "127.0.0.1",
          "--port",
          String(port),
          "--strictPort",
        ],
        { cwd: dashboardRoot, stdio: "ignore", detached: true },
      );
      cleanup.push(() => {
        try {
          process.kill(-preview.pid, "SIGTERM");
        } catch {
          /* already gone */
        }
      });
      opts.vueUrl = `http://127.0.0.1:${port}/`;
      await waitForServer(opts.vueUrl, "vite preview");
    }

    // --- Mock side ----------------------------------------------------
    if (!process.argv.includes("--mock-url")) {
      const { server, port } = await serveStatic(designDir, DEFAULT_MOCK_PORT);
      console.log(`[visual-diff] serving design/ on :${port}`);
      cleanup.push(() => server.close());
      opts.mockUrl = `http://127.0.0.1:${port}/map-c-skyrim.dc.html`;
      await waitForServer(opts.mockUrl, "design static");
    }

    // --- Screenshots --------------------------------------------------
    const vuePng = path.join(opts.out, "vue.png");
    const mockPng = path.join(opts.out, "mock.png");
    const diffPng = path.join(opts.out, "diff.png");
    const browser = await chromium.launch();
    try {
      console.log(`[visual-diff] screenshot Vue  <- ${opts.vueUrl}`);
      await screenshot(browser, opts.vueUrl, vuePng);
      console.log(`[visual-diff] screenshot mock <- ${opts.mockUrl}`);
      await screenshot(browser, opts.mockUrl, mockPng);
    } finally {
      await browser.close();
    }

    // --- Compare ------------------------------------------------------
    const a = PNG.sync.read(readFileSync(vuePng));
    const b = PNG.sync.read(readFileSync(mockPng));
    if (a.width !== b.width || a.height !== b.height) {
      console.warn(
        `[visual-diff] size mismatch: vue ${a.width}x${a.height} vs mock ${b.width}x${b.height} — diff skipped`,
      );
      process.exit(1);
    }
    const diff = new PNG({ width: a.width, height: a.height });
    const mismatched = pixelmatch(a.data, b.data, diff.data, a.width, a.height, {
      threshold: 0.1,
    });
    writeFileSync(diffPng, PNG.sync.write(diff));
    const pct = (mismatched / (a.width * a.height)) * 100;
    console.log(
      `[visual-diff] ${mismatched.toLocaleString()} / ${(a.width * a.height).toLocaleString()} pixels differ (${pct.toFixed(2)}%)`,
    );
    console.log("[visual-diff] per-region:");
    for (const note of regionNotes(a, b)) console.log(note);
    console.log(`[visual-diff] wrote ${diffPng}`);
  } finally {
    for (const fn of cleanup) fn();
  }
}

main().catch((err) => {
  console.error(`[visual-diff] FAILED: ${err.message}`);
  process.exit(1);
});
