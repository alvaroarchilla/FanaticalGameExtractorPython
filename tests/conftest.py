import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--url",
        action="store",
        default="https://www.fanatical.com/",
        help="URL inicial para abrir en el test"
    )
    parser.addoption(
        "--html-output",
        action="store",
        default=None,
        help="Nombre base del archivo HTML (sin extensión)"
    )
    parser.addoption(
        "--pretty",
        action="store_true",
        default=False,
        help="Genera HTML con estilo enriquecido (imagen, marco dorado local MP). "
             "No alarga el scrape: solo cambia el render del reporte."
    )
    # ELIMINADO --headed (ya lo trae pytest-playwright)


@pytest.fixture(scope="session")
def pretty_report(request) -> bool:
    return bool(request.config.getoption("--pretty"))


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Viewport ancho para que 'View on Steam' (d-md-inline) esté disponible."""
    return {
        **browser_context_args,
        "viewport": {"width": 1400, "height": 900},
    }
