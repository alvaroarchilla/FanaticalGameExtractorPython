#!/usr/bin/env python3
"""
Compara los listados actuales de Fanatical / Humble con data/known_bundles.json.

Salida (GitHub Actions via GITHUB_OUTPUT):
  changed=true|false
  source=none|fanatical|humble|both
  new_fanatical=<n>
  new_humble=<n>

Si known_bundles.json no existe o está vacío, solo guarda el baseline (changed=false).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data" / "known_bundles.json"
sys.path.insert(0, str(ROOT))

from pages.humble_bundle_page import HumbleBundlePage, GAMES_LIST_URL  # noqa: E402
from tests.fanatical_listing import (  # noqa: E402
    BUNDLES_LIST_URL,
    collect_pick_and_mix_urls,
    dismiss_language_banner,
)


def _write_output(key: str, value: str) -> None:
    line = f"{key}={value}"
    print(f"[check] {line}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _load_known() -> dict:
    if not STATE_PATH.exists():
        return {"fanatical": [], "humble": [], "updated_at": None}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"fanatical": [], "humble": [], "updated_at": None}


def _save_known(fanatical: list[str], humble: list[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fanatical": sorted(fanatical),
        "humble": sorted(humble),
    }
    STATE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[check] Guardado {STATE_PATH}")


def _fetch_current() -> tuple[list[str], list[str]]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})

        # Fanatical
        page_f = context.new_page()
        print(f"[check] Fanatical listado: {BUNDLES_LIST_URL}")
        page_f.goto(BUNDLES_LIST_URL, wait_until="domcontentloaded", timeout=60000)
        dismiss_language_banner(page_f)
        fanatical = collect_pick_and_mix_urls(page_f)
        print(f"[check] Fanatical: {len(fanatical)} bundles")
        page_f.close()

        # Humble
        page_h = context.new_page()
        print(f"[check] Humble listado: {GAMES_LIST_URL}")
        page_h.goto(GAMES_LIST_URL, wait_until="domcontentloaded", timeout=60000)
        humble_page = HumbleBundlePage(page_h)
        humble_page.handle_popups()
        humble = humble_page.collect_bundle_urls()
        print(f"[check] Humble: {len(humble)} bundles")
        page_h.close()

        browser.close()
    return fanatical, humble


def main() -> int:
    known = _load_known()
    prev_f = set(known.get("fanatical") or [])
    prev_h = set(known.get("humble") or [])

    current_f, current_h = _fetch_current()
    set_f, set_h = set(current_f), set(current_h)

    # Primera ejecución: solo baseline
    if not prev_f and not prev_h:
        _save_known(current_f, current_h)
        print("[check] Baseline inicial guardado (sin publicar)")
        _write_output("changed", "false")
        _write_output("source", "none")
        _write_output("new_fanatical", "0")
        _write_output("new_humble", "0")
        return 0

    new_f = sorted(set_f - prev_f)
    new_h = sorted(set_h - prev_h)

    print(f"[check] Nuevos Fanatical ({len(new_f)}):")
    for u in new_f:
        print(f"  + {u}")
    print(f"[check] Nuevos Humble ({len(new_h)}):")
    for u in new_h:
        print(f"  + {u}")

    # Actualizar siempre al snapshot actual (también quita bundles que ya no están)
    _save_known(current_f, current_h)

    if not new_f and not new_h:
        print("[check] Sin bundles nuevos")
        _write_output("changed", "false")
        _write_output("source", "none")
        _write_output("new_fanatical", "0")
        _write_output("new_humble", "0")
        return 0

    if new_f and new_h:
        source = "both"
    elif new_f:
        source = "fanatical"
    else:
        source = "humble"

    _write_output("changed", "true")
    _write_output("source", source)
    _write_output("new_fanatical", str(len(new_f)))
    _write_output("new_humble", str(len(new_h)))
    print(f"[check] Publicar source={source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
