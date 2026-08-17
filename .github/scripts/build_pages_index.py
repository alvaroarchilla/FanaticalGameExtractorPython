#!/usr/bin/env python3
"""Genera site/index.html enlazando los reportes combinados disponibles."""
from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
SITE = ROOT / "site"

SITE.mkdir(parents=True, exist_ok=True)

candidates = [
    ("Fanatical — all pick-and-mix", "all_fanatical_pick_and_mix_combined_pretty.html"),
    ("Fanatical — all pick-and-mix", "all_fanatical_pick_and_mix_combined.html"),
    ("Humble — all game bundles", "all_humble_game_bundles_combined_pretty.html"),
    ("Humble — all game bundles", "all_humble_game_bundles_combined.html"),
]

links = []
seen_labels = set()
for label, name in candidates:
    src = REPORTS / name
    if not src.exists():
        continue
    # Preferir pretty si ya añadimos el label
    if label in seen_labels:
        continue
    dest = SITE / name
    if not dest.exists():
        dest.write_bytes(src.read_bytes())
    seen_labels.add(label)
    links.append((label, name))

if not links:
    # Página mínima si el scrape falló: evita deploy vacío
    body_links = "<p>No combined reports were generated in this run.</p>"
else:
    items = "\n".join(
        f'<li><a href="{html.escape(name)}">{html.escape(label)}</a></li>'
        for label, name in links
    )
    body_links = f"<ul>\n{items}\n</ul>"

index = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bundle Game Reports</title>
  <style>
    :root {{
      --bg: #0f1419;
      --text: #e8eef4;
      --muted: #9aa8b5;
      --accent: #3d9cf0;
      --panel: #1a222c;
    }}
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: "Segoe UI", system-ui, sans-serif;
      color: var(--text);
      background:
        radial-gradient(900px 400px at 10% 0%, #1e3a5f 0%, transparent 55%),
        var(--bg);
    }}
    main {{
      background: var(--panel); border: 1px solid #2a3644; border-radius: 14px;
      padding: 2rem 2.25rem; max-width: 36rem; width: calc(100% - 2rem);
    }}
    h1 {{ margin: 0 0 0.4rem; font-size: 1.6rem; }}
    p {{ color: var(--muted); margin: 0 0 1.25rem; line-height: 1.45; }}
    ul {{ margin: 0; padding-left: 1.2rem; }}
    li {{ margin: 0.55rem 0; }}
    a {{ color: var(--accent); font-weight: 600; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main>
    <h1>Bundle Game Reports</h1>
    <p>Combined Steam-enriched reports from Fanatical pick-and-mix and/or Humble Bundle listings.</p>
    {body_links}
  </main>
</body>
</html>
"""

(SITE / "index.html").write_text(index, encoding="utf-8")
print(f"Wrote {SITE / 'index.html'} with {len(links)} report link(s)")
