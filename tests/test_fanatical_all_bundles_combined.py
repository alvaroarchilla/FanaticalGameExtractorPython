import pytest
from playwright.sync_api import Page
from tests.test_fanatical_all_bundles import (
    BUNDLES_LIST_URL,
    _collect_bundle_urls,
    _dismiss_language_banner,
)
from tests.utils_html_report import generar_html_combinado_desde_urls


def test_all_bundles_combined(page: Page, pretty_report: bool, request):
    """
    Igual que test_all_bundles, pero un solo HTML con todos los juegos.
    En Links: Steam + enlace Fanatical del pick-and-mix de origen.
    Compatible con --pretty y --html-output.
    """
    output_name = request.config.getoption("--html-output") or "all_fanatical_pick_and_mix_combined"

    print("\n" + "=" * 70)
    print("EXTRACCION COMBINADA (un solo HTML)")
    if pretty_report:
        print("Modo --pretty: reporte enriquecido")
    print("=" * 70)

    print(f"\n[1/3] Cargando listado: {BUNDLES_LIST_URL}")
    page.goto(BUNDLES_LIST_URL, wait_until="domcontentloaded")
    _dismiss_language_banner(page)
    print(f"Pagina cargada: {page.title()}")

    print("\n[2/3] Extrayendo URLs pick-and-mix...")
    absolute_urls = _collect_bundle_urls(page)
    print(f"Total pick-and-mix unicos: {len(absolute_urls)}")
    for i, u in enumerate(absolute_urls, 1):
        print(f"  {i}. {u}")
    print("-" * 70)

    assert absolute_urls, (
        "No se encontraron pick-and-mix en el listado. "
        "La pagina no cargo HitCards a tiempo o cambio el DOM."
    )

    print("\n[3/3] Procesando bundles -> HTML unico...")
    path = generar_html_combinado_desde_urls(
        page,
        absolute_urls,
        pretty=pretty_report,
        output_name=output_name,
        output_dir="reports",
        list_url=BUNDLES_LIST_URL,
        merge_duplicates=True,
    )

    print("\n" + "=" * 70)
    print(f"Reporte combinado: {path}")
    print("=" * 70 + "\n")

    assert path, "No se genero el HTML combinado"
