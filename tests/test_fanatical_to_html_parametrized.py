import pytest
import time
import html
import re
from utils.driver_factory import create_driver
from pages.fanatical_home_page import FanaticalHomePage
from pages.steam_game_page import SteamGamePage, SteamGamePageData

# Mapeo de meses abreviados en español a número
MESES_ES = {
    "ENE": "01", "FEB": "02", "MAR": "03", "ABR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AGO": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DIC": "12"
}

def fecha_a_iso(fecha_str):
    """Convierte '4 AGO 2022' -> '2022-08-04' para ordenación."""
    try:
        partes = fecha_str.strip().split()
        if len(partes) == 3:
            dia, mes_abbr, anio = partes
            mes_num = MESES_ES.get(mes_abbr.upper())
            if mes_num:
                return f"{anio}-{mes_num}-{int(dia):02d}"
    except Exception:
        pass
    return fecha_str

def _sanitize(value: str) -> str:
    """Escapa HTML y normaliza saltos de línea."""
    if value is None or str(value).strip() == "":
        return "N/A"
    text = str(value).strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "; ")
    return html.escape(text)

@pytest.fixture
def driver():
    driver = create_driver()
    yield driver
    driver.quit()

def test_fanatical_to_html_parametrized(driver, request):
    # Leer parámetros
    start_url = request.config.getoption("--url")
    output_name = request.config.getoption("--output")

    # 1. Abrir URL inicial
    driver.get(start_url)
    time.sleep(1)

    # Obtener título de la página
    page_title = driver.title.strip() or "Steam Games Report"

    # Si no se pasa --output, generar nombre de archivo a partir del título
    if not output_name:
        safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", page_title)
        output_name = safe_title.lower()

    home_page = FanaticalHomePage(driver)
    home_page.handle_popups()

    # 2. Obtener lista de bundles
    bundles = home_page.get_bundle_items()
    print(f"Se encontraron {len(bundles)} bundles.")

    # 3. Cabecera HTML con DataTables y título dinámico
    html_head = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{html.escape(page_title)}</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top; }}
            th {{ background-color: #f4f4f4; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1><a href="{html.escape(start_url)}" target="_blank">{html.escape(page_title)}</a></h1>
        <table id="gamesTable">
            <thead>
                <tr>
                    <th>Game Name</th>
                    <th>URL</th>
                    <th>Price</th>
                    <th>Reviews</th>
                    <th>Categories</th>
                    <th>Game Label</th>
                    <th>Release Date</th>
                    <th>Editor</th>
                    <th>Developer</th>
                </tr>
            </thead>
            <tbody>
    """

    rows_html = []

    # 4. Iterar sobre cada bundle
    for idx, bundle in enumerate(bundles, start=1):
        try:
            bundle.click()
            time.sleep(1)
            if not home_page.click_view_on_steam_button(idx):
                continue

            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(0.5)

            steam_page = SteamGamePage(driver)
            steam_page.handle_initial_overlays()

            game_name = steam_page.get_generic_data(SteamGamePageData.GAME_NAME)
            url = steam_page.get_generic_data(SteamGamePageData.URL)
            price = steam_page.get_generic_data(SteamGamePageData.PRICE)
            reviews = steam_page.get_generic_data(SteamGamePageData.REVIEWS)
            categories = steam_page.get_generic_data(SteamGamePageData.CATEGORIES)
            game_label = steam_page.get_generic_data(SteamGamePageData.GAME_LABEL)
            release_date = steam_page.get_generic_data(SteamGamePageData.RELEASE_DATE)
            editor = steam_page.get_generic_data(SteamGamePageData.EDITOR)
            developer = steam_page.get_generic_data(SteamGamePageData.DEVELOPER)

            iso_date = fecha_a_iso(release_date)
            release_date_cell = f'<td data-order="{iso_date}">{_sanitize(release_date)}</td>'

            row_html = f"""
            <tr>
                <td>{_sanitize(game_name)}</td>
                <td><a href="{html.escape(url)}" target="_blank">{html.escape(url)}</a></td>
                <td>{_sanitize(price)}</td>
                <td>{_sanitize(reviews)}</td>
                <td>{_sanitize(categories)}</td>
                <td>{_sanitize(game_label)}</td>
                {release_date_cell}
                <td>{_sanitize(editor)}</td>
                <td>{_sanitize(developer)}</td>
            </tr>
            """
            rows_html.append(row_html)

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        except Exception as e:
            print(f"[{idx}] Error procesando bundle: {e}")
            if len(driver.window_handles) > 1:
                #driver.close()
                driver.switch_to.window(driver.window_handles[0])

    # 5. Pie HTML con DataTables
    html_tail = """
            </tbody>
        </table>
        <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script>
        $(document).ready(function() {
            $('#gamesTable').DataTable({
                pageLength: 25,
                order: [[6, 'desc']],
                language: { url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json" }
            });
        });
        </script>
    </body>
    </html>
    """

    # 6. Guardar HTML
    output_file = f"{output_name}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_head + " \n ".join(rows_html) + html_tail)

    print(f"\n✅ Reporte HTML interactivo generado: {output_file}")
