"""Resolve explicit research workspace context from a URL.

Each page's workspace is determined by an explicit query scope
(``expedition``, ``leg``, ``focus_id``) rather than solely by
server-global mutable state. This module parses that scope, validates
it, and can emit scoped absolute-path links.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

from clawmarks.focus_store import (
    FocusIntegrityError,
    FocusNotFound,
    FocusValidationError,
    Scope,
)


class ContextQueryError(ValueError):
    """Raised when an explicit workspace query is partial, repeated, or mismatched."""


@dataclass(frozen=True)
class WorkspaceContext:
    """Immutable per-request workspace description."""

    expedition: str | None = None
    leg: str | None = None
    focus: dict[str, Any] | None = None


_CONTEXT_KEYS = ("expedition", "leg", "focus_id")


def _single_value(query: dict[str, list[str]], key: str) -> str | None:
    if key not in query:
        return None
    return query[key][0]


def resolve_workspace_context(
    raw_url: str,
    active_selection: dict,
    focus_store,
) -> WorkspaceContext:
    """Derive a :class:`WorkspaceContext` from an explicit URL and browsing state.

    Parameters
    ----------
    raw_url:
        The raw request-target (e.g. ``/map.html?expedition=demo&leg=round1``).
    active_selection:
        Current server-side selection ``{"expedition": ..., "leg": ...}`` used
        only when the URL carries no explicit scope. The dict is never mutated.
    focus_store:
        A :class:`~clawmarks.focus_store.FocusStore` used to load a Focus when
        ``focus_id`` is present.

    Returns
    -------
    WorkspaceContext
        With ``expedition``, ``leg``, and ``focus`` (the full Focus record or
        ``None``).

    Raises
    ------
    ContextQueryError
        If a context key appears more than once, if only a subset of the
        required keys is supplied, or if the referenced Focus cannot be loaded.
    """
    parsed = urlparse(raw_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)

    for key in _CONTEXT_KEYS:
        if key in qs and len(qs[key]) > 1:
            raise ContextQueryError(f"repeated value for {key}: {qs[key]}")

    expedition_q = _single_value(qs, "expedition")
    leg_q = _single_value(qs, "leg")
    focus_id_q = _single_value(qs, "focus_id")

    has_expedition = "expedition" in qs
    has_leg = "leg" in qs
    has_focus = "focus_id" in qs

    if has_focus:
        if not has_expedition or not has_leg:
            raise ContextQueryError(
                "explicit Focus context requires all three: expedition, leg, focus_id"
            )
        if not expedition_q or not leg_q or not focus_id_q:
            raise ContextQueryError(
                "explicit Focus context requires all three: expedition, leg, focus_id"
            )

        try:
            scope = Scope(expedition_q, leg_q)
            focus_record = focus_store.get(scope, focus_id_q)
        except (FocusNotFound, FocusIntegrityError, FocusValidationError) as exc:
            raise ContextQueryError(f"Focus not found or mismatched: {focus_id_q}") from exc

        return WorkspaceContext(
            expedition=expedition_q, leg=leg_q, focus=focus_record
        )

    if has_expedition or has_leg:
        if not (has_expedition and has_leg):
            raise ContextQueryError(
                "partial scope: expedition and leg must be provided together"
            )
        if not expedition_q or not leg_q:
            raise ContextQueryError(
                "partial scope: expedition and leg must be provided together"
            )
        return WorkspaceContext(expedition=expedition_q, leg=leg_q, focus=None)

    expedition_active = None
    leg_active = None
    if isinstance(active_selection, dict):
        expedition_active = active_selection.get("expedition")
        leg_active = active_selection.get("leg")

    return WorkspaceContext(
        expedition=expedition_active, leg=leg_active, focus=None
    )


def context_url(
    path: str, context: WorkspaceContext, include_focus: bool = True
) -> str:
    """Build an absolute-path URL that preserves the given workspace context.

    Any query parameters already present in ``path`` are preserved verbatim
    when they are passed explicitly by the caller. The function never copies
    query parameters from an arbitrary source URL; it only uses ``path`` and
    ``context``.

    Parameters
    ----------
    path:
        Absolute path optionally containing a query string, e.g.
        ``/map.html`` or ``/map.html?tag=a``.
    context:
        The workspace context whose ``expedition``/``leg``/``focus_id`` should
        be emitted.
    include_focus:
        When ``False``, the focus_id is omitted even if ``context.focus`` is
        present.

    Returns
    -------
    str
        A URL such as
        ``/redundancy.html?expedition=demo&leg=round1&focus_id=focus_abcd``.
    """
    parsed = urlparse(path)
    base_path = parsed.path if parsed.path else ""
    if not base_path:
        base_path = path.split("?")[0].split("#")[0]
    if base_path and not base_path.startswith("/"):
        base_path = "/" + base_path
    if not base_path:
        base_path = "/"

    existing = parse_qs(parsed.query, keep_blank_values=True)

    result: dict[str, list[str]] = {key: list(values) for key, values in existing.items()}

    if context.expedition is not None:
        result["expedition"] = [context.expedition]
    else:
        result.pop("expedition", None)

    if context.leg is not None:
        result["leg"] = [context.leg]
    else:
        result.pop("leg", None)

    if include_focus and context.focus is not None:
        focus_id: str | None = None
        if isinstance(context.focus, dict):
            raw = context.focus.get("focus_id")
            if isinstance(raw, str) and raw:
                focus_id = raw
        if focus_id is not None:
            result["focus_id"] = [focus_id]
        else:
            result.pop("focus_id", None)
    else:
        result.pop("focus_id", None)

    encoded = urlencode(result, doseq=True)
    if encoded:
        return f"{base_path}?{encoded}"
    return base_path


def generated_image_url(
    tag: str, context: WorkspaceContext, thumbnail: bool = False
) -> str:
    """Build a leg-scoped URL for one generated image or its thumbnail."""
    encoded_tag = quote(tag, safe="")
    path = f"/thumbs/{encoded_tag}.jpg" if thumbnail else f"/generated/{encoded_tag}"
    return context_url(path, context, include_focus=False)
