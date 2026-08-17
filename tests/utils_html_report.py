import html
import re
import os
from playwright.sync_api import Page
from pages.fanatical_home_page import FanaticalHomePage
from pages.steam_game_page import SteamGamePage


MESES_ES = {
    "ENE": "01", "FEB": "02", "MAR": "03", "ABR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AGO": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DIC": "12"
}

# Pantalla compartida / local (EN + ES). No incluir solo Online / Remote Play Together.
_LOCAL_SHARED_PATTERNS = (
    r"shared\s*/\s*split\s*screen",
    r"shared\s*screen",
    r"split\s*screen",
    r"local\s*multiplayer",
    r"local\s*co-?op",
    r"couch\s*co-?op",
    r"\d+\s*player\s*local",
    r"pantalla\s*compartida",
    r"pantalla\s*dividida",
    r"multijugador\s*local",
    r"cooperativo\s*local",
)
_LOCAL_SHARED_RE = re.compile("|".join(_LOCAL_SHARED_PATTERNS), re.IGNORECASE)


def fecha_a_iso(fecha_str: str) -> str:
    """Convierte '4 AGO 2022' -> '2022-08-04' para ordenación."""
    try:
        partes = fecha_str.strip().split()
        if len(partes) == 3:
            dia, mes_abbr, anio = partes
            mes_num = MESES_ES.get(mes_abbr.upper())
            if mes_num:
                return f"{anio}-{mes_num}-{int(dia):02d}"
    except Exception:
        pass
    return fecha_str


def _sanitize(value: str) -> str:
    """Escapa HTML y normaliza saltos de línea a '; '."""
    if not value or str(value).strip() == "":
        return "N/A"
    return html.escape(str(value).strip().replace("\n", "; "))


def _parse_review_count(token: str) -> int:
    """'1,211' / '1.211' / '1211' -> int."""
    digits = re.sub(r"[^\d]", "", token or "")
    return int(digits) if digits else 0


def reviews_sort_key(reviews_text: str | None) -> int:
    """
    Clave numérica para ordenar por reviews (desc = mejores arriba).
    - Con % global real: 1_000_000 * pct + count  (ej. 82% y 1211 -> 82001211)
    - Sin % (solo 'N reseñas' / N/A): solo el count (0..999999) -> siempre por debajo
    """
    text = (reviews_text or "").strip()
    global_line = ""
    for line in text.splitlines():
        if line.lower().startswith("global"):
            global_line = line
            break
    if not global_line:
        global_line = text

    m_pct = re.search(r"(\d+)\s*%\s*\(([\d.,\s]+)\)", global_line)
    if m_pct:
        pct = int(m_pct.group(1))
        count = _parse_review_count(m_pct.group(2))
        return pct * 1_000_000 + min(count, 999_999)

    m_only = re.search(r"([\d.,]+)\s*reseñas", global_line, flags=re.IGNORECASE)
    if m_only:
        return min(_parse_review_count(m_only.group(1)), 999_999)
    return 0


def _sanitize_reviews(value: str) -> str:
    """Global primero y 30 días debajo, con espacio entre ambos (sin estilos extra)."""
    if not value or str(value).strip() == "":
        return "N/A"
    text = str(value).strip().replace("\r\n", "\n").replace("\r", "\n")
    global_line = ""
    recent_line = ""
    other = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("global"):
            global_line = html.escape(line)
        elif low.startswith("30"):
            recent_line = html.escape(line)
        else:
            other.append(html.escape(line))

    parts = []
    if global_line:
        parts.append(global_line)
    if recent_line:
        parts.append(recent_line)
    parts.extend(other)
    return "<br><br>".join(parts) if parts else "N/A"


def is_local_shared_screen(game_data: dict) -> bool:
    """True si categories/tags indican 2+ jugadores en pantalla compartida / local."""
    blob = " ".join(
        [
            str(game_data.get("categories") or ""),
            str(game_data.get("game_label") or ""),
        ]
    )
    return bool(_LOCAL_SHARED_RE.search(blob))


def _tiers_html(tiers_info: dict | None, pretty: bool = False) -> str:
    """Bloque superior con mensaje y tiers del pick-and-mix (tiers en línea)."""
    if not tiers_info:
        return ""
    summary = (tiers_info.get("summary") or "").strip()
    tiers = tiers_info.get("tiers") or []
    if not summary and not tiers:
        return ""

    lines = []
    if summary:
        lines.append(f"<p>{html.escape(summary)}</p>")
    if tiers:
        chips = []
        for t in tiers:
            qty = html.escape(t.get("quantity") or "")
            price = html.escape(t.get("price") or "")
            per = html.escape(t.get("per_item") or "Per item")
            chip_cls = "tier-item tier-chip" if pretty else "tier-item"
            chips.append(f'<span class="{chip_cls}">{qty}: {price} / {per}</span>')
        lines.append('<div class="tier-row">' + " · ".join(chips) + "</div>")
    cls = "bundle-tiers bundle-tiers--pretty" if pretty else "bundle-tiers"
    return f'<div class="{cls}">\n' + "\n".join(lines) + "\n</div>\n"


def _game_name_cell(game_data: dict, pretty: bool) -> str:
    name = _sanitize(game_data.get("game_name"))
    if not pretty:
        return name

    img = (game_data.get("header_image") or "").strip()
    fallbacks = game_data.get("header_image_fallbacks") or []
    if isinstance(fallbacks, str):
        fallbacks = [fallbacks] if fallbacks else []
    local = is_local_shared_screen(game_data)
    badge = (
        '<span class="local-badge" title="Pantalla compartida / multijugador local">'
        "Local / Shared Screen</span>"
        if local
        else ""
    )
    if img:
        safe_img = html.escape(img, quote=True)
        fb = html.escape("|".join(fallbacks), quote=True)
        return (
            f'<div class="game-name-cell">'
            f'<img class="game-cover" src="{safe_img}" alt="" loading="lazy" '
            f'data-fallbacks="{fb}" onerror="window.__coverFallback&&__coverFallback(this)">'
            f'<div class="game-name-overlay">'
            f'<span class="game-name-text">{name}</span>{badge}'
            f"</div></div>"
        )
    return (
        f'<div class="game-name-cell game-name-cell--plain">'
        f'<div class="game-name-overlay">'
        f'<span class="game-name-text">{name}</span>{badge}'
        f"</div></div>"
    )


def _bundle_store_label(url: str) -> str:
    u = (url or "").lower()
    if "humblebundle.com" in u:
        return "Humble"
    if "fanatical.com" in u:
        return "Fanatical"
    return "Bundle"


def _url_cell(game_data: dict, pretty: bool) -> str:
    """Celda Links: Steam (+ bundle Fanatical/Humble si viene en game_data)."""
    url = game_data.get("url") or "#"
    safe_steam = html.escape(url)

    parts: list[str] = []
    if pretty:
        parts.append(
            f'<a class="steam-link" href="{safe_steam}" target="_blank" title="{safe_steam}">Steam</a>'
        )
    else:
        parts.append(f'<a href="{safe_steam}" target="_blank">{safe_steam}</a>')

    bundles = game_data.get("bundle_links") or []
    if not bundles:
        b_url = (game_data.get("bundle_url") or "").strip()
        if b_url:
            bundles = [{
                "url": b_url,
                "name": game_data.get("bundle_name") or _bundle_label_from_url(b_url),
            }]

    for b in bundles:
        b_url = (b.get("url") or "").strip()
        if not b_url:
            continue
        b_name = (b.get("name") or _bundle_label_from_url(b_url)).strip() or "Bundle"
        store = _bundle_store_label(b_url)
        safe_b = html.escape(b_url)
        safe_name = html.escape(b_name)
        link_cls = "humble-link" if store == "Humble" else "fanatical-link"
        if pretty:
            parts.append(
                f'<a class="{link_cls}" href="{safe_b}" target="_blank" '
                f'title="{safe_b}">{html.escape(store)}: {safe_name}</a>'
            )
        else:
            parts.append(
                f'<a href="{safe_b}" target="_blank">{html.escape(store)}: {safe_name}</a>'
            )

    return f'<div class="links-cell">{"<br>".join(parts)}</div>'


def _bundle_label_from_url(url: str) -> str:
    m = re.search(r"/pick-and-mix/([^/?#]+)", url or "")
    if m:
        return m.group(1).replace("-", " ").strip()
    m = re.search(r"/bundle/([^/?#]+)", url or "")
    if m:
        return m.group(1).replace("-", " ").strip()
    m = re.search(r"/games/([^/?#]+)", url or "")
    if m:
        return m.group(1).replace("-", " ").strip()
    return "Bundle"


def _build_row(game_data: dict, pretty: bool = False) -> str:
    """Genera una fila HTML a partir de un dict de datos del juego."""
    iso_date = fecha_a_iso(game_data.get("release_date", ""))
    release_date_raw = game_data.get("release_date", "N/A")
    reviews_raw = game_data.get("reviews") or ""
    reviews_order = reviews_sort_key(reviews_raw)
    local = pretty and is_local_shared_screen(game_data)
    row_cls = ' class="row-local-mp"' if local else ""
    local_order = "1" if local else "0"

    return f"""
    <tr{row_cls} data-local-mp="{local_order}">
        <td class="col-name" data-order="{html.escape(str(game_data.get('game_name') or ''))}">{_game_name_cell(game_data, pretty)}</td>
        <td class="col-url">{_url_cell(game_data, pretty)}</td>
        <td class="col-price">{_sanitize(game_data.get("price"))}</td>
        <td data-order="{reviews_order}" class="reviews-cell col-reviews">{_sanitize_reviews(reviews_raw)}</td>
        <td class="col-cats">{_sanitize(game_data.get("categories"))}</td>
        <td class="col-labels">{_sanitize(game_data.get("game_label"))}</td>
        <td class="col-date" data-order="{iso_date}">{_sanitize(release_date_raw)}</td>
        <td class="col-editor">{_sanitize(game_data.get("editor"))}</td>
        <td class="col-dev">{_sanitize(game_data.get("developer"))}</td>
        {f'<td data-order="{local_order}">{local_order}</td>' if pretty else ''}
    </tr>
    """


def _classic_css() -> str:
    return """
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top; }
        th { background-color: #f4f4f4; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .reviews-cell { white-space: nowrap; line-height: 1.5; }
        .bundle-tiers { margin: 12px 0 24px 0; }
        .tier-row { margin-top: 8px; }
        .tier-item { white-space: nowrap; }
        .links-cell { line-height: 1.5; }
    """


def _pretty_css() -> str:
    return """
        :root {
            --bg: #0f1419;
            --panel: #1a222c;
            --text: #e8eef4;
            --muted: #9aa8b5;
            --accent: #3d9cf0;
            --gold: #e0b52a;
            --row-alt: #151c24;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            padding: 28px 24px 48px;
            font-family: "Segoe UI", "Trebuchet MS", sans-serif;
            color: var(--text);
            background:
                radial-gradient(1200px 500px at 10% -10%, #1e3a5f 0%, transparent 55%),
                radial-gradient(900px 400px at 100% 0%, #2a1f0a 0%, transparent 50%),
                var(--bg);
        }
        h1 { margin: 0 0 8px; font-size: 1.65rem; font-weight: 700; letter-spacing: 0.02em; }
        h1 a { color: var(--text); text-decoration: none; border-bottom: 2px solid var(--accent); }
        h1 a:hover { color: var(--accent); }
        .legend {
            display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
            margin: 10px 0 18px; color: var(--muted); font-size: 0.92rem;
        }
        .legend-swatch {
            display: inline-block; width: 22px; height: 14px; border-radius: 3px;
            border: 2px solid var(--gold); background: var(--panel); vertical-align: middle;
        }
        .bundle-tiers--pretty {
            background: var(--panel); border: 1px solid #2a3644; border-radius: 10px;
            padding: 14px 16px; margin: 0 0 22px; color: var(--muted);
        }
        .bundle-tiers--pretty .tier-chip {
            display: inline-block; margin: 4px 2px; padding: 4px 10px;
            background: #243040; border-radius: 999px; color: var(--text); white-space: nowrap;
        }
        table.dataTable {
            border-collapse: separate !important; border-spacing: 0 12px; width: 100% !important;
            background: transparent; table-layout: fixed;
        }
        table.dataTable thead th {
            background: #243040; color: var(--text); border: none !important;
            padding: 12px 10px; font-weight: 600; white-space: nowrap;
        }
        table.dataTable tbody td {
            background: var(--panel); border: 1px solid #2a3644 !important;
            border-left: none !important; border-right: none !important;
            padding: 10px 12px; vertical-align: middle; color: var(--text);
        }
        table.dataTable tbody td:first-child {
            border-left: 1px solid #2a3644 !important; border-radius: 10px 0 0 10px;
        }
        table.dataTable tbody td:nth-child(9) {
            border-right: 1px solid #2a3644 !important; border-radius: 0 10px 10px 0;
        }
        table.dataTable tbody tr:nth-child(even) td { background: var(--row-alt); }

        /* Marco dorado limpio (sin degradado L->R ni sombras inset) */
        table.dataTable tbody tr.row-local-mp td {
            border-top-color: var(--gold) !important;
            border-bottom-color: var(--gold) !important;
            background: var(--panel) !important;
        }
        table.dataTable tbody tr.row-local-mp td:first-child {
            border-left: 3px solid var(--gold) !important;
        }
        table.dataTable tbody tr.row-local-mp td:nth-child(9) {
            border-right: 3px solid var(--gold) !important;
        }

        .col-name { width: 26%; }
        .col-url { width: 9%; text-align: center; }
        .col-price { width: 7%; white-space: nowrap; }
        .col-reviews { width: 11%; }
        .col-cats { width: 15%; word-break: break-word; line-height: 1.35; }
        .col-labels { width: 13%; word-break: break-word; line-height: 1.35; }
        .col-date { width: 8%; white-space: nowrap; }
        .col-editor, .col-dev { width: 7%; word-break: break-word; }

        .links-cell {
            display: flex; flex-direction: column; gap: 6px; align-items: center;
        }
        .steam-link, .fanatical-link, .humble-link {
            display: inline-block; padding: 4px 10px; border-radius: 6px;
            text-decoration: none; font-weight: 600; font-size: 0.78rem;
            max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .steam-link {
            background: #243040; color: var(--accent) !important;
        }
        .steam-link:hover { background: #2f4054; }
        .fanatical-link {
            background: #2a2418; color: #f0c14b !important; border: 1px solid #6b5420;
        }
        .fanatical-link:hover { background: #3a3220; }
        .humble-link {
            background: #1a2a22; color: #6fcf97 !important; border: 1px solid #2d6a4f;
        }
        .humble-link:hover { background: #243830; }

        .game-name-cell {
            position: relative; min-height: 130px; height: 130px;
            border-radius: 8px; overflow: hidden; background: #121820;
        }
        .game-name-cell--plain { background: #243040; }
        .game-cover {
            position: absolute; inset: 0; width: 100%; height: 100%;
            object-fit: cover; object-position: center center;
            filter: brightness(1.22) contrast(1.08) saturate(1.08);
        }
        .game-name-overlay {
            position: relative; z-index: 1; height: 100%;
            display: flex; flex-direction: column; justify-content: flex-end; gap: 6px;
            padding: 12px 14px;
            background: linear-gradient(
                180deg,
                rgba(8,12,18,0.05) 0%,
                rgba(8,12,18,0.18) 50%,
                rgba(8,12,18,0.62) 100%
            );
        }
        .game-name-text {
            color: #fff; font-weight: 700; font-size: 1.05rem; line-height: 1.25;
            text-shadow: 0 1px 2px rgba(0,0,0,0.85), 0 0 6px rgba(0,0,0,0.45);
        }
        .local-badge {
            align-self: flex-start; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em;
            text-transform: uppercase; color: #1a1405;
            background: linear-gradient(180deg, #f0d060, #c99612);
            border: 1px solid #ffe08a; border-radius: 4px; padding: 2px 8px;
        }
        .reviews-cell { white-space: nowrap; line-height: 1.5; color: var(--muted); }
        a { color: var(--accent); }
        .dataTables_wrapper .dataTables_filter input,
        .dataTables_wrapper .dataTables_length select {
            background: var(--panel); color: var(--text); border: 1px solid #2a3644; border-radius: 6px;
            padding: 4px 8px;
        }
        .dataTables_wrapper .dataTables_info,
        .dataTables_wrapper .dataTables_length,
        .dataTables_wrapper .dataTables_filter,
        .dataTables_wrapper .dataTables_paginate { color: var(--muted); }
        .dataTables_wrapper .dataTables_paginate .paginate_button {
            color: var(--muted) !important;
        }
        .dataTables_wrapper .dataTables_paginate .paginate_button.current {
            background: #243040 !important; border-color: var(--accent) !important; color: var(--text) !important;
        }
    """


def _legend_html(pretty: bool) -> str:
    if not pretty:
        return ""
    return (
        '<div class="legend">'
        '<span class="legend-swatch" aria-hidden="true"></span>'
        "<span>Marco dorado = pantalla compartida / multijugador local (2+ jugadores)</span>"
        "</div>"
    )


def _html_shell(
    page_title: str,
    start_url: str,
    tiers_info: dict | None,
    pretty: bool,
) -> tuple[str, str]:
    css = _pretty_css() if pretty else _classic_css()
    local_th = '<th class="col-local">Local</th>' if pretty else ""
    if pretty:
        dt_opts = """
            pageLength: 25,
            order: [[9, 'desc'], [6, 'desc']],
            columnDefs: [{ targets: 9, visible: false, searchable: false }],
            language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json" }
        """
        cover_js = """
    <script>
    window.__coverFallback = function(img) {
        var list = (img.getAttribute('data-fallbacks') || '').split('|').filter(Boolean);
        if (!list.length) { img.remove(); return; }
        img.setAttribute('data-fallbacks', list.slice(1).join('|'));
        img.src = list[0];
    };
    </script>
"""
    else:
        dt_opts = """
            pageLength: 25,
            order: [[6, 'desc']],
            language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json" }
        """
        cover_js = ""
    url_th = "Links"
    head = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{html.escape(page_title)}</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>{css}</style>
</head>
<body>
    <h1><a href="{html.escape(start_url)}" target="_blank">{html.escape(page_title)}</a></h1>
    {_legend_html(pretty)}
    {_tiers_html(tiers_info, pretty=pretty)}
    <table id="gamesTable" class="display">
        <thead>
            <tr>
                <th>Game Name</th>
                <th>{url_th}</th>
                <th>Price</th>
                <th>Reviews</th>
                <th>Categories</th>
                <th>Game Label</th>
                <th>Release Date</th>
                <th>Editor</th>
                <th>Developer</th>
                {local_th}
            </tr>
        </thead>
        <tbody>
"""
    tail = f"""
        </tbody>
    </table>
    {cover_js}
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>
    $(document).ready(function() {{
        $('#gamesTable').DataTable({{{dt_opts}}});
    }});
    </script>
</body>
</html>
"""
    return head, tail


def _recover_to_fanatical(page: Page, start_url: str, home_page: FanaticalHomePage):
    page.goto(start_url, wait_until="domcontentloaded")
    home_page.handle_popups()
    home_page.wait_for_product_grid()


def _close_extra_pages(page: Page):
    for p in page.context.pages:
        if p != page:
            try:
                p.close()
            except Exception:
                pass


def _game_merge_key(game_data: dict) -> str:
    url = game_data.get("url") or ""
    m = re.search(r"/app/(\d+)", url)
    if m:
        return f"app:{m.group(1)}"
    name = (game_data.get("game_name") or "").strip().casefold()
    return f"name:{name}" if name else f"id:{id(game_data)}"


def _attach_bundle_link(game_data: dict, bundle_url: str, bundle_name: str | None = None) -> None:
    name = (bundle_name or "").strip() or _bundle_label_from_url(bundle_url)
    link = {"url": bundle_url, "name": name}
    existing = game_data.setdefault("bundle_links", [])
    if not any((b.get("url") or "").rstrip("/") == bundle_url.rstrip("/") for b in existing):
        existing.append(link)
    game_data["bundle_url"] = bundle_url
    game_data["bundle_name"] = name


def extraer_juegos_desde_bundle(
    page: Page,
    start_url: str,
    pretty: bool = False,
    bundle_name: str | None = None,
) -> tuple[str, dict | None, list[dict]]:
    """
    Abre un pick-and-mix Fanatical y extrae juegos de Steam.
    Devuelve (titulo_pagina, tiers_info, lista de game_data).
    Cada game_data incluye bundle_url / bundle_links hacia start_url.
    """
    page.goto(start_url, wait_until="domcontentloaded")
    page_title = page.title().strip() or "Steam Games Report"
    b_name = (bundle_name or page_title).strip()

    home_page = FanaticalHomePage(page)
    home_page.handle_popups()

    tiers_info = home_page.get_bundle_tiers()
    jobs = home_page.collect_jobs()
    print(f"Trabajos a procesar en Steam: {len(jobs)}" + (" [pretty]" if pretty else ""))

    games: list[dict] = []
    steam = SteamGamePage(page)

    for i, job in enumerate(jobs):
        try:
            if job["type"] == "steam":
                print(f"[Steam] [{i+1}/{len(jobs)}] {job['title']} -> {job['steam_url']}")
                data = steam.open_url_and_extract_data(
                    job["steam_url"], game_name=job["title"], include_image=pretty
                )
                if data:
                    _attach_bundle_link(data, start_url, b_name)
                    games.append(data)
            elif job["type"] == "search":
                print(f"[Steam] [{i+1}/{len(jobs)}] Busqueda por nombre: {job['title']}")
                data = steam.open_game_by_name_and_extract_data(
                    job["title"], include_image=pretty
                )
                if data:
                    _attach_bundle_link(data, start_url, b_name)
                    games.append(data)
            elif job["type"] == "bundle":
                print(
                    f"[Steam] [{i+1}/{len(jobs)}] Bundle '{job['title']}' "
                    f"({len(job['game_names'])} juegos)"
                )
                bundle_anchor = job["game_names"][0] if job["game_names"] else job["title"]
                for game_name in job["game_names"]:
                    data = steam.open_game_by_name_and_extract_data(
                        game_name, include_image=pretty
                    )
                    if data:
                        data["game_name"] = (
                            f"{data['game_name']} *bundled with {bundle_anchor}"
                        )
                        _attach_bundle_link(data, start_url, b_name)
                        games.append(data)
        except Exception as e:
            print(f"[Steam] Error en trabajo {i} ({job.get('title')}): {e}")

    return page_title, tiers_info, games


def _rows_from_games(games: list[dict], pretty: bool) -> list[str]:
    rows = [_build_row(g, pretty=pretty) for g in games]
    if pretty:
        rows.sort(key=lambda row: (0 if 'class="row-local-mp"' in row else 1))
    return rows


def _write_report(
    page_title: str,
    start_url: str,
    tiers_info: dict | None,
    games: list[dict],
    pretty: bool,
    output_name: str | None = None,
    output_dir: str = "reports",
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", page_title).lower()
    html_head, html_tail = _html_shell(page_title, start_url, tiers_info, pretty)
    rows_html = _rows_from_games(games, pretty)

    base = output_name or safe_title
    if pretty and not str(base).endswith("_pretty"):
        base = f"{base}_pretty"
    output_path = os.path.join(output_dir, f"{base}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_head + "\n".join(rows_html) + html_tail)
    print(f"Reporte generado: {output_path} ({len(games)} juegos)")
    return output_path


def generar_html_desde_url(
    page: Page,
    start_url: str,
    pretty: bool = False,
    output_name: str | None = None,
    output_dir: str = "reports",
) -> str:
    """Genera un reporte HTML desde una URL de Fanatical (Playwright)."""
    page_title, tiers_info, games = extraer_juegos_desde_bundle(
        page, start_url, pretty=pretty
    )
    return _write_report(
        page_title,
        start_url,
        tiers_info,
        games,
        pretty=pretty,
        output_name=output_name,
        output_dir=output_dir,
    )


def generar_html_combinado_desde_urls(
    page: Page,
    bundle_urls: list[str],
    pretty: bool = False,
    output_name: str | None = None,
    output_dir: str = "reports",
    list_url: str = "https://www.fanatical.com/en/bundle/games",
    merge_duplicates: bool = True,
) -> str:
    """
    Procesa varios pick-and-mix y escribe UN solo HTML.
    En Links: Steam + enlace(s) Fanatical del bundle de origen.
    Si merge_duplicates=True, un mismo juego (appid) acumula varios enlaces Fanatical.
    """
    merged: dict[str, dict] = {}
    ordered: list[dict] = []
    bundles_ok = 0
    bundles_fail = 0

    for i, url in enumerate(bundle_urls, 1):
        print(f"\n{'=' * 70}")
        print(f"[Combinado {i}/{len(bundle_urls)}] {url}")
        print(f"{'=' * 70}")
        bundle_page = page.context.new_page()
        try:
            _title, _tiers, games = extraer_juegos_desde_bundle(
                bundle_page, url, pretty=pretty
            )
            bundles_ok += 1
            for g in games:
                if not merge_duplicates:
                    ordered.append(g)
                    continue
                key = _game_merge_key(g)
                if key not in merged:
                    merged[key] = g
                    ordered.append(g)
                else:
                    # Acumular enlaces Fanatical en la fila ya existente
                    for b in g.get("bundle_links") or []:
                        _attach_bundle_link(
                            merged[key],
                            b.get("url") or url,
                            b.get("name"),
                        )
            print(f"Bundle combinado #{i}: +{len(games)} juegos")
        except Exception as e:
            bundles_fail += 1
            print(f"Error en bundle combinado #{i}: {e}")
        finally:
            try:
                bundle_page.close()
            except Exception:
                pass
            try:
                for p in page.context.pages:
                    if p != page:
                        p.close()
            except Exception:
                pass

    page_title = f"All Fanatical Pick-and-Mix ({len(ordered)} games, {bundles_ok} bundles)"
    summary = {
        "summary": (
            f"Combinado de {bundles_ok} pick-and-mix "
            f"({bundles_fail} fallidos). Listado: {list_url}"
        ),
        "tiers": [],
    }
    base = output_name or "all_fanatical_pick_and_mix_combined"
    return _write_report(
        page_title,
        list_url,
        summary,
        ordered,
        pretty=pretty,
        output_name=base,
        output_dir=output_dir,
    )
