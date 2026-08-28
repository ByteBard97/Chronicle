// Click-to-zoom for Mermaid diagrams.
//
// Material renders each diagram's SVG inside a CLOSED shadow root
// (verified by reading Material's own bundled JS:
// `r.attachShadow({mode:"closed"})`) attached directly to the `.mermaid`
// element itself. That means this script can never read or clone the
// rendered SVG (`.mermaid svg` always returns nothing from outside a
// closed shadow root, regardless of timing) -- an earlier version of
// this file tried exactly that and silently did nothing. It also means
// this script must NOT touch mermaid's own render/init calls (that
// broke diagram rendering entirely once already this project).
//
// The fix: don't reach into the shadow content at all. Toggle a class
// on the `.mermaid` HOST element itself; CSS (stylesheets/extra.css)
// does the rest via `position`/`transform` on that host, which the
// browser applies to its shadow-rendered content transparently, the
// same way any element's layout affects what's inside it. The dimmed
// backdrop is a separate, plain light-DOM element this script owns
// directly -- not a shadow-DOM trick.
//
// Wiring: deliberately polls for `.mermaid` elements on an interval
// rather than relying on Material's `document$` firing at a useful
// time -- empirically, `document$` fires for this script before
// Material's own `.mermaid` conversion has run, so `.mermaid` matches
// zero elements at that point every time. Polling is slower but
// actually correct; re-verify with real timing evidence (not
// assumption) before switching back to an event-driven approach.
(function () {
  var backdrop = null;

  function close() {
    var zoomed = document.querySelector(".mermaid.mermaid-zoomed");
    if (zoomed) zoomed.classList.remove("mermaid-zoomed");
    if (backdrop) {
      backdrop.remove();
      backdrop = null;
    }
    document.body.classList.remove("mermaid-zoom-active");
    document.removeEventListener("keydown", onKeydown);
  }

  function open(container) {
    container.classList.add("mermaid-zoomed");
    backdrop = document.createElement("div");
    backdrop.className = "mermaid-zoom-backdrop";
    backdrop.addEventListener("click", close);
    document.body.appendChild(backdrop);
    document.body.classList.add("mermaid-zoom-active");
    document.addEventListener("keydown", onKeydown);
  }

  function onKeydown(event) {
    if (event.key === "Escape") close();
  }

  function wireUp() {
    document.querySelectorAll(".mermaid").forEach(function (container) {
      if (container.dataset.zoomWired) return;
      container.dataset.zoomWired = "true";
      container.addEventListener("click", function () {
        if (container.classList.contains("mermaid-zoomed")) {
          close();
        } else {
          open(container);
        }
      });
    });
  }

  function startPolling() {
    var tries = 0;
    var interval = setInterval(function () {
      wireUp();
      tries += 1;
      if (tries > 40) clearInterval(interval); // ~12s ceiling
    }, 300);
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(startPolling);
  } else if (typeof document !== "undefined" && document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startPolling);
  } else {
    startPolling();
  }
})();
