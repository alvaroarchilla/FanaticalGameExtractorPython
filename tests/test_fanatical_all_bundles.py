import pytest
from playwright.sync_api import Page
from tests.fanatical_listing import (
    BUNDLES_LIST_URL,
    collect_pick_and_mix_urls,
    dismiss_language_banner,
)
from tests.utils_html_report import generar_html_desde_url


def test_all_bundles(page: Page, pretty_report: bool):
    print("\n" + "=" * 70)
    print("INICIANDO EXTRACCION DE PICK-AND-MIX (listado /en/bundle/games)")
    if pretty_report:
        print("Modo --pretty: reporte enriquecido (mismo scrape)")
    print("=" * 70)

    print(f"\n[1/3] Cargando listado: {BUNDLES_LIST_URL}")
    page.goto(BUNDLES_LIST_URL, wait_until="domcontentloaded")
    dismiss_language_banner(page)
    print(f"Pagina cargada: {page.title()}")

    print("\n[2/3] Extrayendo URLs pick-and-mix (HitCards)...")
    absolute_urls = collect_pick_and_mix_urls(page)
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
