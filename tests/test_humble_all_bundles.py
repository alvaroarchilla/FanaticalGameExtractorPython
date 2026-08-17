from playwright.sync_api import Page

from pages.humble_bundle_page import HumbleBundlePage, GAMES_LIST_URL
from tests.utils_humble_html_report import generar_html_humble_desde_url


def test_humble_all_bundles(page: Page, pretty_report: bool):
    """Procesa todos los bundles de /games y genera un HTML por cada uno."""
    print("\n" + "=" * 70)
    print("INICIANDO EXTRACCION HUMBLE (listado /games)")
    if pretty_report:
        print("Modo --pretty")
    print("=" * 70)

    print(f"\n[1/3] Cargando listado: {GAMES_LIST_URL}")
    page.goto(GAMES_LIST_URL, wait_until="domcontentloaded", timeout=60000)
    humble = HumbleBundlePage(page)
    humble.handle_popups()
    print(f"Pagina cargada: {page.title()}")

    print("\n[2/3] Extrayendo URLs de bundles...")
    urls = humble.collect_bundle_urls()
    for i, u in enumerate(urls, 1):
        print(f"  {i}. {u}")
    print("-" * 70)

    assert urls, "No se encontraron bundles en https://www.humblebundle.com/games"

    print("\n[3/3] Procesando bundles...")
    ok = fail = 0
    for i, url in enumerate(urls, 1):
        print(f"\n{'=' * 70}")
        print(f"[{i}/{len(urls)}] {url}")
        print(f"{'=' * 70}")
        try:
            bundle_page = page.context.new_page()
            generar_html_humble_desde_url(bundle_page, url, pretty=pretty_report)
            ok += 1
            bundle_page.close()
        except Exception as e:
            fail += 1
            print(f"Error en bundle #{i}: {e}")
            try:
                for p in page.context.pages:
                    if p != page:
                        p.close()
            except Exception:
                pass

    print("\n" + "=" * 70)
    print("RESUMEN HUMBLE")
    print(f"   Total: {len(urls)}  Exitosos: {ok}  Fallidos: {fail}")
    print("=" * 70 + "\n")
    assert ok > 0, "Ningun bundle Humble se proceso correctamente"
