# conftest.py
def pytest_addoption(parser):
    parser.addoption(
        "--url",
        action="store",
        default="https://www.fanatical.com/",
        help="URL inicial para abrir en el test"
    )
    parser.addoption(
        "--output",
        action="store",
        default=None,
        help="Nombre base del archivo HTML (sin extensión). Si no se pasa, se genera a partir del título de la página."
    )
