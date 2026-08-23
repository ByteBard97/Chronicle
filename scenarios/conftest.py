"""Scenario-suite wiring for the frame log, plus the pytest deep-link mechanism.

Every scenario runs through chronicle.driver.Driver, which writes a frame
log per run (docs/frame-log-schema.md). The runs directory is overridable
via CHRONICLE_RUNS_DIR -- the one env var shared by pytest and the
dashboard (ui-spec §1.2) -- so this fixture points it at a per-test tmp
dir: scenario runs exercise the same env-var contract the dashboard reads,
without polluting the repo's real runs/ directory.

**Deep links** (docs/dashboard-build-plan.md §2 M1 bullet 2, ui-spec
§1.2's "a pytest-emitted deep link is therefore resolvable by
construction"): a scenario test that wants a failing assertion to carry a
dashboard URL calls the ``deep_link`` fixture to record its run/tick/
selection context; ``pytest_exception_interact`` below reads that context
back off the failing test and appends the URL to the failure output.

Design choice, called out per the work packet's own question: this uses
``pytest_exception_interact`` (a conftest hook), not a fixture-level
try/except. Reasons:

  - a fixture-level try/except can only wrap the parts of the test body
    it can see (e.g. a context manager the test opts into around each
    assertion); a collection hook fires for *any* exception the test
    raises, including a plain ``assert`` with no cooperating wrapper, which
    is how every existing scenario test in this suite is written (see
    ``scenarios/test_jarl_death_belief_cascade.py`` -- bare ``assert``
    statements, no assertion-wrapping helper to hook into).
  - it keeps the opt-in surface to one fixture call (``deep_link.set(...)``)
    per test, rather than requiring every scenario to restructure its body
    around a ``with`` block or a custom assert helper.
  - it composes with pytest's own reporting: the URL is appended as a
    named section on the failure's ``longrepr`` (when the exception repr
    supports it, which pytest's default ``ExceptionChainRepr`` does), so it
    shows up in the normal failure output pytest already prints -- no
    separate summary line to remember to read.

The tradeoff: a test must call ``deep_link.set(...)`` before the
assertion that might fail for the link to have anything to report (there's
no way to conjure ``run_id``/``tick``/``sel`` out of a bare ``assert`` after
the fact) -- documented on the fixture itself.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import pytest

DEFAULT_DASHBOARD_URL = "http://localhost:5173"


@dataclass
class DeepLinkContext:
    """URL-state contract fields a test has supplied so far (ui-spec §1.2).

    Only ``run`` and ``t`` are meaningful on their own; ``sel``/``view``/
    ``panels``/``filters`` are optional context a test can add when it
    knows which entity/record its assertion is about. Values are strings
    (or coerced to strings at URL-build time) -- the URL-state contract's
    query-*value* encoding isn't frozen by ui-spec §1.2 (only the query
    *keys* are named), so this is this lane's own choice, not a frozen
    format.
    """

    run: str | None = None
    branch: str | None = None
    t: int | None = None
    view: str | None = None
    sel: str | None = None
    panels: str | None = None
    filters: str | None = None

    def set(
        self,
        *,
        run: str | None = None,
        branch: str | None = None,
        t: int | None = None,
        view: str | None = None,
        sel: str | None = None,
        panels: str | None = None,
        filters: str | None = None,
    ) -> None:
        """Update whichever fields are given; call again to refine as a test progresses."""
        if run is not None:
            self.run = run
        if branch is not None:
            self.branch = branch
        if t is not None:
            self.t = t
        if view is not None:
            self.view = view
        if sel is not None:
            self.sel = sel
        if panels is not None:
            self.panels = panels
        if filters is not None:
            self.filters = filters

    def url(self, *, base: str | None = None) -> str | None:
        """The dashboard deep link, or None if not enough context was ever set (need at least `run`)."""
        if self.run is None:
            return None
        base_url = base if base is not None else os.environ.get("CHRONICLE_DASHBOARD_URL", DEFAULT_DASHBOARD_URL)
        params: dict[str, str] = {"run": self.run}
        if self.branch is not None:
            params["branch"] = self.branch
        if self.t is not None:
            params["t"] = str(self.t)
        if self.view is not None:
            params["view"] = self.view
        if self.sel is not None:
            params["sel"] = self.sel
        if self.panels is not None:
            params["panels"] = self.panels
        if self.filters is not None:
            params["filters"] = self.filters
        return f"{base_url}/?{urlencode(params)}"


_DEEP_LINK_KEY = pytest.StashKey[DeepLinkContext]()


@pytest.fixture(autouse=True)
def _runs_dir_per_test(tmp_path, monkeypatch):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path / "runs"))
    return tmp_path / "runs"


@pytest.fixture
def deep_link(request: pytest.FixtureRequest) -> DeepLinkContext:
    """Per-test deep-link context. Call ``deep_link.set(run=..., t=..., sel=...)``
    before an assertion that might fail; on failure, the URL it composes
    is appended to the failure output (see ``pytest_exception_interact``
    below). A test that never calls ``.set()`` gets no link -- there's
    nothing to build one from.
    """
    context = DeepLinkContext()
    request.node.stash[_DEEP_LINK_KEY] = context
    return context


def pytest_exception_interact(node: Any, call: Any, report: Any) -> None:
    """On a failing scenario test that registered deep-link context, append its dashboard URL to the failure output."""
    context = node.stash.get(_DEEP_LINK_KEY, None)
    if context is None:
        return
    url = context.url()
    if url is None:
        return
    section = (
        "dashboard deep link",
        f"{url}\n(ui-spec §1.2: run/branch/t/view/sel/panels/filters -- resolvable once the dashboard dev server is up)",
    )
    longrepr = getattr(report, "longrepr", None)
    if hasattr(longrepr, "addsection"):
        longrepr.addsection(*section)
    else:
        # Fallback for a longrepr shape that doesn't support addsection
        # (e.g. a plain string from some non-standard failure path) --
        # still surface the link rather than silently dropping it.
        report.sections.append(section)
