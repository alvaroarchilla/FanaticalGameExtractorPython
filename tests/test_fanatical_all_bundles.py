import pytest
from playwright.sync_api import Page
from pages.fanatical_home_page import FanaticalHomePage
from tests.utils_html_report import generar_html_desde_url

BASE_URL = "https://www.fanatical.com"
BUNDLES_LIST_URL = f"{BASE_URL}/en/bundle/games"


def _dismiss_language_banner(page: Page) -> None:
    """Mantener inglés si aparece el banner de idioma."""
    try:
        btn = page.locator("button:has-text('permanecer')").first
        if btn.is_visible(timeout=1500):
            btn.click(timeout=2000)
    except Exception:
        pass


def _collect_bundle_urls(page: Page) -> list[str]:
    """URLs absolutas de los bundles visibles en el listado (HitCards)."""
    home = FanaticalHomePage(page)
    home.handle_popups()
    _dismiss_language_banner(page)

    # Esperar hidratación React (attached: los del menú pueden no ser visibles)
    page.wait_for_selector("a.HitCard__main__cover", state="attached", timeout=30000)

    # Scroll por si hay lazy-load
    prev = 0
    for _ in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(600)
        n = page.locator("a.HitCard__main__cover").count()
        if n == prev:
            break
        prev = n

    # Solo pick-and-mix: el scraper usa article.PickAndMixCard (no aplica a /bundle/)
    hrefs = page.eval_on_selector_all(
        "a.HitCard__main__cover",
        """els => [...new Set(
            els.map(e => (e.getAttribute('href') || '').split('?')[0])
               .filter(h => h.includes('/pick-and-mix/'))
        )]""",
    )

    absolute = []
    for href in hrefs:
        if href.startswith("http"):
            absolute.append(href)
        else:
            absolute.append(f"{BASE_URL}{href}")
    return absolute


def test_all_bundles(page: Page, pretty_report: bool):
    print("\n" + "=" * 70)
    print("INICIANDO EXTRACCION DE PICK-AND-MIX (listado /en/bundle/games)")
    if pretty_report:
        print("Modo --pretty: reporte enriquecido (mismo scrape)")
    print("=" * 70)

    print(f"\n[1/3] Cargando listado: {BUNDLES_LIST_URL}")
    page.goto(BUNDLES_LIST_URL, wait_until="domcontentloaded")
    _dismiss_language_banner(page)
    print(f"Pagina cargada: {page.title()}")

    print("\n[2/3] Extrayendo URLs pick-and-mix (HitCards)...")
    absolute_urls = _collect_bundle_urls(page)
    print(f"Total pick-and-mix unicos: {len(absolute_urls)}")
    for i, u in enumerate(absolute_urls, 1):
        print(f"  {i}. {u}")
    print("-" * 70)

    assert absolute_urls, (
        "No se encontraron pick-and-mix en el listado. "
        "La pagina no cargo HitCards a tiempo o cambio el DOM."
    )

    print("\n[3/3] Procesando bundles (flujo rapido: collect_jobs + Steam)...")
    total_procesados = 0
    exitosos = 0
    fallidos = 0

    for i, url in enumerate(absolute_urls, 1):
        print(f"\n{'=' * 70}")
        print(f"[{i}/{len(absolute_urls)}] {url}")
        print(f"{'=' * 70}")

        try:
            bundle_page = page.context.new_page()
            generar_html_desde_url(bundle_page, url, pretty=pretty_report)
            exitosos += 1
            print(f"Bundle #{i} completado")
            bundle_page.close()
        except Exception as e:
            fallidos += 1
            print(f"Error en bundle #{i}: {e}")
            try:
                for p in page.context.pages:
                    if p != page:
                        p.close()
            except Exception:
                pass

        total_procesados += 1

    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    print(f"   Total pick-and-mix: {len(absolute_urls)}")
    print(f"   Procesados: {total_procesados}")
    print(f"   Exitosos:   {exitosos}")
    print(f"   Fallidos:   {fallidos}")
    print("=" * 70 + "\n")

    assert exitosos > 0, "Ningun pick-and-mix se proceso correctamente"
