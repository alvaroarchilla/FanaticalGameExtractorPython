"""Generación de reportes HTML para bundles de Humble Bundle."""
from __future__ import annotations

import html
import os
import re

from playwright.sync_api import Page

from pages.humble_bundle_page import HumbleBundlePage, GAMES_LIST_URL
from pages.steam_game_page import SteamGamePage
from tests.utils_html_report import (
    _attach_bundle_link,
    _game_merge_key,
    _sanitize,
    _until_cell,
    _untils_data_attr,
    _upsert_store_deal,
    format_offer_until,
    is_local_shared_screen,
)


def _humble_until_from_html(body: str) -> tuple[str, str]:
    match = re.search(r'"end_time\|datetime":\s*"([^"]+)"', body or "")
    if not match:
        return "", ""
    display, iso = format_offer_until(match.group(1))
    if display:
        print(f"[Humble] Activo hasta {display}")
    return display, iso


def _humble_offer_until(page: Page, start_url: str, captured_html: str = "") -> tuple[str, str]:
    """Fecha hasta la que se puede comprar el bundle (end_time del HTML original)."""
    display, iso = _humble_until_from_html(captured_html)
    if display:
        return display, iso
    try:
        body = page.content()
    except Exception:
        body = ""
    display, iso = _humble_until_from_html(body)
    if display:
        return display, iso
    try:
        resp = page.request.get(start_url, timeout=30000)
        if resp.ok:
            display, iso = _humble_until_from_html(resp.text())
            if display:
                return display, iso
    except Exception as e:
        print(f"[Humble] No se pudo leer la fecha de fin: {e}")
    print("[Humble] Sin end_time")
    return "", ""


def _tiers_html_humble(tiers_info: dict | None, pretty: bool = False) -> str:
    """Bloque superior: cada tier con precio y lista de juegos."""
    if not tiers_info:
        return ""
    tiers = tiers_info.get("tiers") or []
    summary = (tiers_info.get("summary") or "").strip()
    if not tiers and not summary:
        return ""

    lines = []
    if summary:
        lines.append(f"<p>{html.escape(summary)}</p>")

    for t in tiers:
        price = html.escape(t.get("price") or "")
        label = html.escape(t.get("label") or "")
        games = [
            html.escape(it["title"])
            for it in (t.get("items") or [])
            if not it.get("skip")
        ]
        skipped = [
            html.escape(it["title"])
            for it in (t.get("items") or [])
            if it.get("skip")
        ]
        head = price or label
        body = ", ".join(games) if games else "(sin juegos Steam)"
        extra = ""
        if skipped:
            extra = (
                f' <span class="tier-skipped">(+ {len(skipped)} no-juego: '
                f"{', '.join(skipped)})</span>"
            )
        if pretty:
            lines.append(
                f'<div class="tier-row">'
                f'<span class="tier-chip"><strong>{head}</strong> — '
                f"{len(games)} juegos: {body}</span>{extra}</div>"
            )
        else:
            lines.append(
                f"<p><strong>{head}</strong> — {len(games)} juegos: {body}{extra}</p>"
            )

    cls = "bundle-tiers bundle-tiers--pretty" if pretty else "bundle-tiers"
    return f'<div class="{cls}">\n' + "\n".join(lines) + "\n</div>\n"


def _enrich_row_with_tier(game_data: dict) -> dict:
    """Añade el precio de tier Humble al nombre (texto) para visibilidad en tabla."""
    tier = (game_data.get("humble_tier") or "").strip()
    if tier and not str(game_data.get("game_name") or "").endswith(f"[{tier}]"):
        # No mutamos el nombre; la celda Links / badge lo muestra
        pass
    return game_data


def _build_row_humble(game_data: dict, pretty: bool = False) -> str:
    """Fila HTML con columna Tier (precio de desbloqueo Humble)."""
    from tests.utils_html_report import (
        fecha_a_iso,
        reviews_sort_key,
        _sanitize_reviews,
        _game_name_cell,
        _url_cell,
        _bundle_cell,
        _bundles_data_attr,
        _bundle_names,
        _price_cell,
        _money_value,
        _until_cell,
        _untils_data_attr,
    )

    iso_date = fecha_a_iso(game_data.get("release_date", ""))
    release_date_raw = game_data.get("release_date", "N/A")
    reviews_raw = game_data.get("reviews") or ""
    reviews_order = reviews_sort_key(reviews_raw)
    local = pretty and is_local_shared_screen(game_data)
    row_cls = ' class="row-local-mp"' if local else ""
    local_order = "1" if local else "0"
    tier = _sanitize(game_data.get("humble_tier") or "N/A")
    tier_order = re.sub(r"[^\d.]", "", str(game_data.get("humble_tier") or "")) or "0"
    bundles_attr = _bundles_data_attr(game_data)
    untils_attr = _untils_data_attr(game_data)
    bundle_order = html.escape(" | ".join(_bundle_names(game_data)))
    until_html, until_order = _until_cell(game_data)
    price_order = f"{_money_value(str(game_data.get('price') or '')):.4f}"

    return f"""
    <tr{row_cls} data-local-mp="{local_order}" data-bundles="{bundles_attr}" data-untils="{untils_attr}">
        <td class="col-name" data-order="{html.escape(str(game_data.get('game_name') or ''))}">{_game_name_cell(game_data, pretty)}</td>
        <td class="col-url">{_url_cell(game_data, pretty)}</td>
        <td class="col-bundle" data-order="{bundle_order}">{_bundle_cell(game_data, pretty)}</td>
        <td class="col-until" data-order="{html.escape(until_order)}">{until_html}</td>
        <td class="col-tier" data-order="{html.escape(tier_order)}">{tier}</td>
        <td class="col-price" data-order="{price_order}">{_price_cell(game_data)}</td>
        <td data-order="{reviews_order}" class="reviews-cell col-reviews">{_sanitize_reviews(reviews_raw)}</td>
        <td class="col-cats">{_sanitize(game_data.get("categories"))}</td>
        <td class="col-labels">{_sanitize(game_data.get("game_label"))}</td>
        <td class="col-date" data-order="{iso_date}">{_sanitize(release_date_raw)}</td>
        <td class="col-editor">{_sanitize(game_data.get("editor"))}</td>
        <td class="col-dev">{_sanitize(game_data.get("developer"))}</td>
        {f'<td data-order="{local_order}">{local_order}</td>' if pretty else ''}
    </tr>
    """


def _html_shell_humble(
    page_title: str,
    start_url: str,
    tiers_info: dict | None,
    pretty: bool,
) -> tuple[str, str]:
    """Shell HTML con columna Tier; reutiliza CSS pretty/classic del reporte Fanatical."""
    from tests.utils_html_report import (
        _pretty_css,
        _classic_css,
        _legend_html,
        _bundle_filter_toolbar_html,
        _datatable_init_js,
    )

    css = _pretty_css() if pretty else _classic_css()
    # Ajustes de ancho para columna Tier (+ Bundle); última visible = Developer (11)
    css += """
        .col-tier { width: 7%; white-space: nowrap; font-weight: 600; }
        .tier-skipped { color: #9aa8b5; font-size: 0.85em; }
        table.dataTable tbody td:nth-child(12) {
            border-right: 1px solid #2a3644 !important; border-radius: 0 10px 10px 0;
        }
        table.dataTable tbody tr.row-local-mp td:nth-child(12) {
            border-right: 3px solid var(--gold) !important;
        }
        table.dataTable tbody td:nth-child(11) {
            border-right: none !important; border-radius: 0;
        }
        table.dataTable tbody tr.row-local-mp td:nth-child(11) {
            border-right-color: #2a3644 !important; border-right-width: 1px !important;
        }
    """
    local_th = '<th class="col-local">Local</th>' if pretty else ""
    tiers_block = _tiers_html_humble(tiers_info, pretty=pretty)

    if pretty:
        dt_opts = """
            pageLength: 25,
            order: [[12, 'desc'], [4, 'asc'], [9, 'desc']],
            columnDefs: [{ targets: 12, visible: false, searchable: false }],
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
            order: [[4, 'asc'], [9, 'desc']],
            language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json" }
        """
        cover_js = ""

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
    {tiers_block}
    {_bundle_filter_toolbar_html()}
    <table id="gamesTable" class="display">
        <thead>
            <tr>
                <th>Game Name</th>
                <th>Links</th>
                <th>Bundle</th>
                <th>Activo hasta</th>
                <th>Tier</th>
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
    {_datatable_init_js(dt_opts)}
    </script>
</body>
</html>
"""
    return head, tail

def _write_humble_report(
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
    html_head, html_tail = _html_shell_humble(page_title, start_url, tiers_info, pretty)
    rows = [_build_row_humble(g, pretty=pretty) for g in games]
    if pretty:
        rows.sort(key=lambda row: (0 if 'class="row-local-mp"' in row else 1))

    base = output_name or safe_title
    if pretty and not str(base).endswith("_pretty"):
        base = f"{base}_pretty"
    output_path = os.path.join(output_dir, f"{base}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_head + "\n".join(rows) + html_tail)
    print(f"Reporte Humble generado: {output_path} ({len(games)} juegos)")
    return output_path


def extraer_juegos_desde_humble(
    page: Page,
    start_url: str,
    pretty: bool = False,
) -> tuple[str, dict, list[dict]]:
    """
    Abre un bundle Humble, lee tiers/ítems y enriquece con datos Steam.
    """
    captured_html = {"body": ""}

    def _on_document(resp):
        if resp.request.resource_type != "document":
            return
        url = (resp.url or "").split("?")[0].rstrip("/")
        wanted = (start_url or "").split("?")[0].rstrip("/")
        if wanted and wanted not in url:
            return
        try:
            captured_html["body"] = resp.text()
        except Exception:
            pass

    page.on("response", _on_document)
    page.goto(start_url, wait_until="domcontentloaded", timeout=60000)
    humble = HumbleBundlePage(page)
    humble.handle_popups()

    parsed = humble.collect_tier_items()
    page_title = parsed.get("title") or page.title().strip() or "Humble Bundle"
    ends_at, ends_iso = _humble_offer_until(page, start_url, captured_html["body"])
    tiers_info = {
        "summary": f"{page_title} — pay what you want",
        "tiers": parsed.get("tiers") or [],
    }

    steam = SteamGamePage(page)
    games: list[dict] = []
    playable = [it for it in parsed.get("items") or [] if not it.get("skip")]
    print(f"[Humble] Procesando {len(playable)} juegos en Steam "
          f"(omitidos {len(parsed.get('items') or []) - len(playable)} no-juego)")

    for i, it in enumerate(playable, 1):
        title = it["title"]
        print(f"[Steam] [{i}/{len(playable)}] {title} (tier {it.get('tier_price')})")
        try:
            data = steam.open_game_by_name_and_extract_data(
                title, include_image=pretty
            )
            if not data:
                data = {
                    "game_name": title,
                    "url": "#",
                    "price": "N/A",
                    "reviews": "",
                    "categories": "",
                    "game_label": "",
                    "release_date": "",
                    "editor": "",
                    "developer": "",
                }
            data["humble_tier"] = it.get("tier_price") or ""
            data["humble_tier_label"] = it.get("tier_label") or ""
            _upsert_store_deal(data, "Humble", data["humble_tier"])
            # Preferir portada Humble (más clara) y Steam como fallback
            if pretty and it.get("image"):
                steam_img = (data.get("header_image") or "").strip()
                steam_fbs = list(data.get("header_image_fallbacks") or [])
                data["header_image"] = it["image"]
                fallbacks = []
                if steam_img:
                    fallbacks.append(steam_img)
                fallbacks.extend(steam_fbs)
                data["header_image_fallbacks"] = fallbacks
            _attach_bundle_link(data, start_url, page_title, ends_at, ends_iso)
            games.append(data)
        except Exception as e:
            print(f"[Steam] Error con '{title}': {e}")

    return page_title, tiers_info, games


def generar_html_humble_desde_url(
    page: Page,
    start_url: str,
    pretty: bool = False,
    output_name: str | None = None,
    output_dir: str = "reports",
) -> str:
    page_title, tiers_info, games = extraer_juegos_desde_humble(
        page, start_url, pretty=pretty
    )
    return _write_humble_report(
        page_title,
        start_url,
        tiers_info,
        games,
        pretty=pretty,
        output_name=output_name,
        output_dir=output_dir,
    )


def generar_html_humble_combinado(
    page: Page,
    bundle_urls: list[str],
    pretty: bool = False,
    output_name: str | None = None,
    output_dir: str = "reports",
    list_url: str = GAMES_LIST_URL,
    merge_duplicates: bool = True,
) -> str:
    merged: dict[str, dict] = {}
    ordered: list[dict] = []
    all_tiers_summary: list[dict] = []
    ok = 0
    fail = 0

    for i, url in enumerate(bundle_urls, 1):
        print(f"\n{'=' * 70}")
        print(f"[Humble combinado {i}/{len(bundle_urls)}] {url}")
        print(f"{'=' * 70}")
        bundle_page = page.context.new_page()
        try:
            title, tiers_info, games = extraer_juegos_desde_humble(
                bundle_page, url, pretty=pretty
            )
            ok += 1
            all_tiers_summary.append(
                {
                    "price": title,
                    "label": title,
                    "items": [
                        {"title": f"{t.get('price')}: {t.get('game_count', 0)} juegos", "skip": False}
                        for t in (tiers_info.get("tiers") or [])
                    ],
                }
            )
            for g in games:
                if not merge_duplicates:
                    ordered.append(g)
                    continue
                key = _game_merge_key(g)
                # Incluir tier en la clave para no mezclar el mismo juego en tiers distintos
                # de bundles diferentes está bien fusionar; tier se conserva el más bajo
                if key not in merged:
                    merged[key] = g
                    ordered.append(g)
                else:
                    for b in g.get("bundle_links") or []:
                        _attach_bundle_link(
                            merged[key],
                            b.get("url") or url,
                            b.get("name"),
                            b.get("ends_at") or "",
                            b.get("ends_at_iso") or "",
                        )
                    for d in g.get("store_deals") or []:
                        _upsert_store_deal(
                            merged[key],
                            d.get("store") or "",
                            d.get("price") or "",
                            d.get("detail") or "",
                        )
                    # Conservar el tier más barato si hay varios
                    old = merged[key].get("humble_tier") or ""
                    new = g.get("humble_tier") or ""
                    def _num(p):
                        try:
                            return float(re.sub(r"[^\d.]", "", p.replace(",", ".")) or 9999)
                        except Exception:
                            return 9999.0
                    if new and (_num(new) < _num(old) or not old):
                        merged[key]["humble_tier"] = new
                        merged[key]["humble_tier_label"] = g.get("humble_tier_label") or ""
            print(f"Bundle combinado #{i}: +{len(games)} juegos")
        except Exception as e:
            fail += 1
            print(f"Error en bundle Humble #{i}: {e}")
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

    page_title = f"All Humble Game Bundles ({len(ordered)} games, {ok} bundles)"
    tiers_info = {
        "summary": (
            f"Combinado de {ok} bundles de {list_url} "
            f"({fail} fallidos)."
        ),
        "tiers": [],
    }
    base = output_name or "all_humble_game_bundles_combined"
    return _write_humble_report(
        page_title,
        list_url,
        tiers_info,
        ordered,
        pretty=pretty,
        output_name=base,
        output_dir=output_dir,
    )
