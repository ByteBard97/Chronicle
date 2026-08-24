import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { serveRuns } from "./vite-plugins/serveRuns";
import { serveLive } from "./vite-plugins/serveLive";

// Range spike wiring (see README.md "Range spike" for the measured results
// that led here): `vite dev`'s built-in static middleware answers 206 to a
// Range request for `runs/` once `server.fs.allow` lets it follow the
// `dashboard/runs -> ../runs` symlink — but `vite preview` serves only its
// build output and ignores `fs.allow` entirely, so the same request 200s
// with the SPA fallback instead of reaching the file. Rather than ship two
// different code paths (Vite's static handling for dev, nothing for
// preview), `serveRuns()` is the ui-spec §1.3-permitted fallback — a tiny
// Range-aware static file server for `runs/`, mounted identically in both
// `configureServer` and `configurePreviewServer`. It runs ahead of Vite's
// own middleware, so this is the one path exercised by both servers and by
// the standing 206 assertion (scripts/check-range.mjs).
export default defineConfig({
  plugins: [vue(), serveRuns(), serveLive()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
