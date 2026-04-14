"""One-shot inspection script for RCA of a Convênio job.

Uses Supabase REST + Storage HTTP API directly via httpx (already installed in
backend venv). Avoids needing the supabase-py SDK.

Pulls everything needed to produce a triage report for a single job_id:
  - input.pdf (storage: jobs/{job_id}/pdfs/input.pdf)
  - schema.xsd, data.xml, template_name.txt (storage: jobs/{job_id}/assets/)
  - visual_data.json (storage: jobs/{job_id}/visual_data.json)
  - first few screenshots under jobs/{job_id}/screenshots/
  - jobs.result_json from the DB (full pipeline output)

Output goes to /tmp/rca-convenio/<job_id>/.

Usage:
    .venv/Scripts/python.exe scripts/inspect_rca_convenio.py <job_id>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=False)

import httpx  # noqa: E402


def _fmt_bytes(n: int) -> str:
    f = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if f < 1024:
            return f"{f:.1f}{unit}"
        f /= 1024
    return f"{f:.1f}TB"


def _stage_summary(result: dict) -> dict:
    """Extract high-signal fields from each pipeline stage in result_json."""
    summary: dict = {}

    clusters = result.get("clusters") or (result.get("stage1") or {}).get("clusters")
    summary["stage1_clusters"] = {
        "count": len(clusters) if clusters else 0,
        "sample": clusters[:2] if clusters else None,
    }

    pages = result.get("pages") or (result.get("stage2") or {}).get("pages")
    if pages:
        first = pages[0] or {}
        summary["stage2_pages"] = {
            "count": len(pages),
            "first_page_blocks": len(first.get("blocks", [])),
            "first_page_text_len": len(first.get("text", "") or ""),
        }

    layouts = result.get("layouts")
    if layouts:
        summary["stage3_1_layouts"] = [
            {
                "layout_id": l.get("layout_id"),
                "type": l.get("type") or l.get("layout_type"),
                "pages": l.get("pages"),
                "confidence": l.get("confidence"),
            }
            for l in layouts
        ]

    visual = result.get("visual_analysis") or result.get("stage3_2")
    if isinstance(visual, dict):
        summary["stage3_2_visual"] = {
            "consistency": visual.get("consistency_score"),
            "regions": list((visual.get("visual_regions") or {}).keys()),
            "drawn_elements_count": len(visual.get("drawn_elements") or []),
        }

    elements = result.get("elements") or result.get("semantic_elements")
    if elements:
        by_type: dict[str, int] = {}
        for e in elements:
            t = (e or {}).get("type") or (e or {}).get("semantic_type") or "unknown"
            by_type[t] = by_type.get(t, 0) + 1
        summary["stage3_3_elements"] = {"total": len(elements), "by_type": by_type}

    trees = result.get("document_trees") or result.get("hierarchy")
    if trees:
        summary["stage3_4_trees"] = {
            "count": len(trees) if isinstance(trees, list) else 1,
            "sample_keys": list(trees[0].keys())[:10]
            if isinstance(trees, list) and trees and isinstance(trees[0], dict)
            else None,
        }

    mappings = result.get("field_mappings") or result.get("mappings")
    if mappings:
        summary["stage4_mappings"] = {
            "count": len(mappings),
            "with_xsd_path": sum(1 for m in mappings if (m or {}).get("xsd_path")),
            "sample": mappings[:3],
        }
    coverage = result.get("coverage") or result.get("overlay_by_layout")
    if coverage is not None:
        summary["stage4_coverage"] = coverage if isinstance(coverage, (int, float, str)) else "dict"

    template = result.get("template_draft") or result.get("template")
    if template:
        if isinstance(template, dict):
            summary["stage5_template"] = {
                "keys": list(template.keys()),
                "html_len": len(template.get("html", "") or ""),
            }
        else:
            summary["stage5_template"] = {"html_len": len(template or "")}

    summary["top_level_keys"] = sorted(list(result.keys()))
    return summary


def main(job_id: str) -> int:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("!! SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing from env")
        return 1

    out_dir = Path("C:/tmp/rca-convenio") / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[inspect] job_id = {job_id}")
    print(f"[inspect] url    = {url}")
    print(f"[inspect] out    = {out_dir}")

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    with httpx.Client(timeout=60.0, headers=headers) as client:
        # 1) DB row ------------------------------------------------------
        print("\n[1/5] GET /rest/v1/jobs ...")
        r = client.get(
            f"{url}/rest/v1/jobs",
            params={
                "id": f"eq.{job_id}",
                "select": "id,status,created_at,updated_at,result_json",
            },
        )
        if r.status_code != 200:
            print(f"  !! {r.status_code}: {r.text[:200]}")
            return 2
        rows = r.json()
        if not rows:
            print(f"  !! job {job_id} not found")
            return 2
        row = rows[0]
        print(f"  status     = {row.get('status')}")
        print(f"  created_at = {row.get('created_at')}")
        print(f"  updated_at = {row.get('updated_at')}")

        result_json = row.get("result_json") or {}
        (out_dir / "result_json.json").write_text(
            json.dumps(result_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  result_json -> result_json.json ({_fmt_bytes(len(json.dumps(result_json)))})")

        summary = _stage_summary(result_json)
        (out_dir / "stage_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        def _download(path: str, target: Path, label: str) -> bool:
            r2 = client.get(f"{url}/storage/v1/object/jobs/{path}")
            if r2.status_code == 200:
                target.write_bytes(r2.content)
                print(f"  -> {label} ({_fmt_bytes(len(r2.content))})")
                return True
            print(f"  -- {label} not present ({r2.status_code})")
            return False

        # 2) PDF ---------------------------------------------------------
        print("\n[2/5] Downloading input.pdf ...")
        _download(f"jobs/{job_id}/pdfs/input.pdf", out_dir / "input.pdf", "input.pdf")
        # Sometimes upload goes to alternative names
        for alt in ("input_2.pdf", "input_3.pdf"):
            _download(f"jobs/{job_id}/pdfs/{alt}", out_dir / alt, alt)

        # 3) Assets ------------------------------------------------------
        print("\n[3/5] Downloading assets (XSD / XML / template_name) ...")
        for asset in ("schema.xsd", "data.xml", "data.json", "template_name.txt"):
            _download(f"jobs/{job_id}/assets/{asset}", out_dir / asset, asset)

        # 4) visual_data.json -------------------------------------------
        print("\n[4/5] Downloading visual_data.json ...")
        _download(
            f"jobs/{job_id}/visual_data.json",
            out_dir / "visual_data.json",
            "visual_data.json",
        )

        # 5) Screenshots (list + download first few) --------------------
        print("\n[5/5] Listing screenshots ...")
        r3 = client.post(
            f"{url}/storage/v1/object/list/jobs",
            json={
                "prefix": f"jobs/{job_id}/screenshots",
                "limit": 100,
                "offset": 0,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
        if r3.status_code == 200:
            items = r3.json() or []
            names = [i.get("name") for i in items if i.get("name")]
            print(f"  found {len(names)} screenshot(s): {names[:5]}{'...' if len(names) > 5 else ''}")
            shots_dir = out_dir / "screenshots"
            shots_dir.mkdir(exist_ok=True)
            for n in names[:4]:
                _download(f"jobs/{job_id}/screenshots/{n}", shots_dir / n, f"shot:{n}")
        else:
            print(f"  !! list screenshots failed: {r3.status_code}: {r3.text[:200]}")

    # Triage printout ----------------------------------------------------
    print("\n" + "=" * 72)
    print("TRIAGE SUMMARY (full details in stage_summary.json)")
    print("=" * 72)
    for k, v in summary.items():
        if k == "top_level_keys":
            continue
        print(f"\n  {k}:")
        print("    " + json.dumps(v, ensure_ascii=False, default=str)[:600])
    print("\n  top_level_keys in result_json:")
    print(f"    {summary.get('top_level_keys')}")
    print(f"\nArtifacts saved in: {out_dir}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scripts/inspect_rca_convenio.py <job_id>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
