from playwright.sync_api import Page

from pages.humble_bundle_page import HumbleBundlePage, GAMES_LIST_URL
from tests.utils_humble_html_report import generar_html_humble_combinado


def test_humble_all_bundles_combined(page: Page, pretty_report: bool, request):
    """Todos los bundles de /games en un solo HTML (Links: Steam + Humble)."""
    output_name = (
        request.config.getoption("--html-output") or "all_humble_game_bundles_combined"
    )

    print("\n" + "=" * 70)
    print("EXTRACCION HUMBLE COMBINADA (un solo HTML)")
    if pretty_report:
        print("Modo --pretty")
    print("=" * 70)

    print(f"\n[1/3] Cargando listado: {GAMES_LIST_URL}")
    page.goto(GAMES_LIST_URL, wait_until="domcontentloaded", timeout=60000)
    humble = HumbleBundlePage(page)
    humble.handle_popups()

    print("\n[2/3] Extrayendo URLs...")
    urls = humble.collect_bundle_urls()
    for i, u in enumerate(urls, 1):
        print(f"  {i}. {u}")
    assert urls, "No se encontraron bundles en /games"

    print("\n[3/3] Procesando -> HTML unico...")
    path = generar_html_humble_combinado(
        page,
        urls,
        pretty=pretty_report,
        output_name=output_name,
        output_dir="reports",
        list_url=GAMES_LIST_URL,
        merge_duplicates=True,
    )
    print(f"\nReporte combinado: {path}")
    assert path
