/**
 * jsdom stub for `@tanstack/vue-virtual`'s layout reads (test-only helper,
 * shared by every test that mounts `FeedTable`/`FeedScreen`).
 *
 * jsdom reports 0 for every element's `offsetWidth`/`offsetHeight`
 * (`@tanstack/virtual-core`'s `getRect`/`measureElement` read exactly
 * those, not `getBoundingClientRect`). A virtualizer measuring a 0-height
 * scroll container renders zero rows (or overscan-only) — silently, with
 * no error — which makes a naive "renders fewer than 715 rows" assertion
 * pass for the wrong reason (nothing rendered, not "virtualization is
 * windowing correctly"), and can make a "row visible without scrolling"
 * assertion fail for the wrong reason (nothing rendered, not "the
 * scroll-to-tick logic is broken").
 *
 * Call `stubVirtualizerViewport()` in a test (or its `beforeEach`) and
 * call the returned restore function in `afterEach`. The scroll container
 * (`.feed-table__scroll`) gets the fixed viewport height; every other
 * measured element (a row or group-header row) gets a fixed row height —
 * distinct values, so the viewport doesn't itself get measured as "one
 * giant row" and so the test can reason about "how many rows fit."
 */
export function stubVirtualizerViewport(viewportHeightPx = 600, rowHeightPx = 30, groupHeaderHeightPx = 22) {
  const offsetHeightDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight");
  const offsetWidthDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth");
  const clientHeightDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientHeight");
  const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;

  function heightFor(el: HTMLElement): number {
    if (el.classList.contains("feed-table__scroll")) return viewportHeightPx;
    // Distinct from a plain row's height so Observer's variable-height
    // group-header rows actually exercise measureElement's heterogeneous
    // path, rather than every measured element collapsing to one value.
    if (el.querySelector?.(".feed-group-header") || el.classList.contains("feed-group-header")) {
      return groupHeaderHeightPx;
    }
    return rowHeightPx;
  }

  Object.defineProperty(HTMLElement.prototype, "offsetHeight", {
    configurable: true,
    get(this: HTMLElement) {
      return heightFor(this);
    },
  });
  Object.defineProperty(HTMLElement.prototype, "offsetWidth", {
    configurable: true,
    get() {
      return 800;
    },
  });
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get(this: HTMLElement) {
      return heightFor(this);
    },
  });
  Element.prototype.getBoundingClientRect = function (this: Element) {
    const height = this instanceof HTMLElement ? heightFor(this) : rowHeightPx;
    return {
      width: 800,
      height,
      top: 0,
      left: 0,
      right: 800,
      bottom: height,
      x: 0,
      y: 0,
      toJSON() {
        return this;
      },
    } as DOMRect;
  };

  return function restore() {
    if (offsetHeightDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "offsetHeight", offsetHeightDescriptor);
    }
    if (offsetWidthDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "offsetWidth", offsetWidthDescriptor);
    }
    if (clientHeightDescriptor) {
      Object.defineProperty(HTMLElement.prototype, "clientHeight", clientHeightDescriptor);
    }
    Element.prototype.getBoundingClientRect = originalGetBoundingClientRect;
  };
}
