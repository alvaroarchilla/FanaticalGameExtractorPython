import pytest
import csv
import time
from utils.driver_factory import create_driver
from pages.fanatical_home_page import FanaticalHomePage
from pages.steam_game_page import SteamGamePage, SteamGamePageData

@pytest.fixture
def driver():
    driver = create_driver()
    yield driver
    driver.quit()

def test_fanatical_to_steam_scraper(driver):
    home_page = FanaticalHomePage(driver)

    # 1. Abrir Fanatical y cerrar pop-ups
    home_page.open_home()
    home_page.handle_popups()

    # 2. Ir a categoría de juegos
   # home_page.go_to_games_category()

    # 3. Obtener lista de bundles
    bundles = home_page.get_bundle_items()
    print(f"Se encontraron {len(bundles)} bundles.")

    # 4. Preparar CSV
    csv_filename = "steam_games_report.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Game Name", "URL", "Price", "Reviews", "Categories",
            "Game Label", "Release Date", "Editor", "Developer"
        ])

        # 5. Iterar sobre cada bundle
        for idx, bundle in enumerate(bundles, start=1):
            try:
                # Clic en el bundle
                bundle.click()
                time.sleep(1)  # Pequeña espera para que cargue

                # Buscar y abrir enlace de Steam
                if home_page.is_element_present(home_page.VIEW_ON_STEAM):
                    home_page.click(home_page.VIEW_ON_STEAM)
                elif home_page.is_element_present(home_page.VIEW):
                    home_page.click(home_page.VIEW)
                else:
                    print(f"[{idx}] No se encontró enlace de Steam.")
                    driver.back()
                    continue

                # 6. Cambiar a la nueva pestaña
                driver.switch_to.window(driver.window_handles[-1])
                time.sleep(1)  # Pequeña espera para que cargue

                # 7. Interactuar con SteamGamePage
                steam_page = SteamGamePage(driver)
                steam_page.handle_initial_overlays()

                # 8. Extraer datos
                row = [
                    steam_page.get_generic_data(SteamGamePageData.GAME_NAME),
                    steam_page.get_generic_data(SteamGamePageData.URL),
                    steam_page.get_generic_data(SteamGamePageData.PRICE),
                    steam_page.get_generic_data(SteamGamePageData.REVIEWS),
                    steam_page.get_generic_data(SteamGamePageData.CATEGORIES),
                    steam_page.get_generic_data(SteamGamePageData.GAME_LABEL),
                    steam_page.get_generic_data(SteamGamePageData.RELEASE_DATE),
                    steam_page.get_generic_data(SteamGamePageData.EDITOR),
                    steam_page.get_generic_data(SteamGamePageData.DEVELOPER)
                ]
                writer.writerow(row)

                print(f"[{idx}] Datos guardados: {row}")

                # 9. Cerrar pestaña de Steam y volver a Fanatical
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

            except Exception as e:
                print(f"[{idx}] Error procesando bundle: {e}")
                # Intentar volver a la pestaña principal
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
    with open("steam_games_report.csv", mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            print(row)
    print(f"\n✅ Reporte generado: {csv_filename}")
