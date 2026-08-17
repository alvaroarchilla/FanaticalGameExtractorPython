import re
from playwright.sync_api import Page
from tests.utils_html_report import generar_html_desde_url


def test_fanatical_to_html_parametrized(page: Page, request, pretty_report: bool):
    start_url = request.config.getoption("--url")
    output_name = request.config.getoption("--html-output")

    if not output_name:
        # Nombre provisional; generar_html_desde_url lo normaliza con el título real
        output_name = None
    else:
        output_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", output_name).lower()

    # Sin --pretty: reporte clásico rápido (mismo scrape).
    # Con --pretty: HTML enriquecido; imagen vía appid CDN (casi sin coste extra).
    path = generar_html_desde_url(
        page,
        start_url,
        pretty=pretty_report,
        output_name=output_name,
        output_dir="." if output_name else "reports",
    )
    print(f"\nReporte HTML interactivo generado: {path}")
