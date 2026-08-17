from playwright.sync_api import Page
from tests.utils_humble_html_report import generar_html_humble_desde_url


def test_humble_to_html_parametrized(page: Page, request, pretty_report: bool):
    """Genera un HTML a partir de una URL de bundle Humble (--url)."""
    start_url = request.config.getoption("--url")
    output_name = request.config.getoption("--html-output")

    if not start_url or "humblebundle.com" not in start_url:
        # Default útil si no pasan --url
        start_url = "https://www.humblebundle.com/games/awesome-indie-adventures"

    path = generar_html_humble_desde_url(
        page,
        start_url,
        pretty=pretty_report,
        output_name=output_name,
        output_dir="reports",
    )
    print(f"\nReporte Humble generado: {path}")
    assert path
