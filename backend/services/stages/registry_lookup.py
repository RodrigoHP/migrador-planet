"""Stage 11 — Registry Lookup.

Queries the Supabase `layout_registry` table for each LayoutType fingerprint
hash.  If a match is found, marks the LayoutType as reusable and stores the
existing template_id.  If no match is found, the LayoutType is left as "new"
and the pipeline continues normally.

If Supabase is not configured or is unreachable, emits a warning SSE event and
skips the lookup entirely — the pipeline is never blocked by registry
unavailability.

Registers itself in the default_registry as Stage 11 (Block 3).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from models.layout_type import LayoutType

logger = logging.getLogger(__name__)

_WARNING_MESSAGE = "Registry indisponível — layout tratado como novo"


# ---------------------------------------------------------------------------
# Supabase client helper
# ---------------------------------------------------------------------------


def _get_supabase_client() -> Optional[Any]:
    """Return a Supabase client or None if credentials are missing / library unavailable."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")

    if not url or not key:
        return None

    try:
        from supabase import create_client  # type: ignore[import]
        return create_client(url, key)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Registry query
# ---------------------------------------------------------------------------


def _lookup_fingerprint(
    client: Any, fingerprint_hash: str
) -> Optional[str]:
    """Query layout_registry for the given hash.

    Returns the template_id string if found, else None.
    Raises on genuine errors (connection issues, unexpected responses).
    """
    response = (
        client.table("layout_registry")
        .select("template_id")
        .eq("fingerprint_hash", fingerprint_hash)
        .limit(1)
        .execute()
    )
    data = getattr(response, "data", None) or []
    if data:
        return data[0].get("template_id")
    return None


# ---------------------------------------------------------------------------
# Stage executor
# ---------------------------------------------------------------------------


async def execute(context: Dict[str, Any]) -> Dict[str, Any]:
    """Stage 11 executor — Registry Lookup.

    Reads context["_layout_type_objects"] (list of LayoutType).
    Updates is_reusable / template_id on each LayoutType in-place.
    Re-serialises context["layout_types"].
    """
    emit = context.get("emit_progress")

    layout_types: List[LayoutType] = context.get("_layout_type_objects", [])

    hits = 0
    misses = 0
    skipped = False

    # Attempt to get a Supabase client
    client: Optional[Any] = None
    try:
        client = _get_supabase_client()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialise Supabase client: %s", exc)
        client = None

    if client is None:
        # Emit warning SSE and skip lookup
        skipped = True
        warning_msg = _WARNING_MESSAGE
        logger.warning(warning_msg)

        if emit:
            try:
                emit(
                    {
                        "stage": 11,
                        "stage_name": "Registry Lookup",
                        "status": "completed",
                        "warning": warning_msg,
                        "summary": {
                            "skipped": True,
                            "reason": warning_msg,
                        },
                    }
                )
            except Exception:  # noqa: BLE001
                pass

        # Re-serialise without changes
        context["layout_types"] = [lt.to_dict() for lt in layout_types]
        return {"skipped": True, "hits": 0, "misses": 0}

    # Perform lookup for each LayoutType
    for lt in layout_types:
        fph = lt.fingerprint.fingerprint_hash
        if not fph:
            misses += 1
            continue
        try:
            template_id = _lookup_fingerprint(client, fph)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Registry lookup failed for hash %s: %s", fph, exc)
            # Treat as miss — do not block pipeline
            misses += 1
            continue

        if template_id:
            lt.is_reusable = True
            lt.template_id = template_id
            hits += 1
        else:
            misses += 1

    # Re-serialise
    context["layout_types"] = [lt.to_dict() for lt in layout_types]

    if emit:
        try:
            emit(
                {
                    "stage": 11,
                    "stage_name": "Registry Lookup",
                    "status": "completed",
                    "summary": {
                        "hits": hits,
                        "misses": misses,
                        "skipped": skipped,
                    },
                }
            )
        except Exception:  # noqa: BLE001
            pass

    return {"hits": hits, "misses": misses, "skipped": skipped}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register(registry) -> None:  # type: ignore[type-arg]
    """Replace the stub Stage 11 in the given registry with this implementation."""
    registry.remove_stage(11)
    registry.register_stage(
        stage_number=11,
        name="Registry Lookup",
        block_id=3,
        estimated_duration=0.5,
        execute_fn=execute,
    )
