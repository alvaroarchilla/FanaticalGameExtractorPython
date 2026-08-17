import pytest
import csv
import re
from playwright.sync_api import Page
from pages.fanatical_home_page import FanaticalHomePage
from pages.steam_game_page import SteamGamePage, SteamGamePageData


def test_fanatical_to_steam_scraper(page: Page):
    home_page = FanaticalHomePage(page)

    # 1. Abrir Fanatical y cerrar pop-ups
    print("[1/9] Abriendo Fanatical...")
    home_page.open_home()
    home_page.handle_popups()

    # Obtener título para generar nombre de archivo
    page_title = page.title().strip() or "Steam Games Report"
    safe_title = re.sub(r"[^a-zA-Z0-9_-]+", "_", page_title).lower()
    csv_filename = f"{safe_title}.csv"

    # 2. Obtener lista de bundles
    print("[2/9] Obteniendo bundles...")
    bundles = home_page.get_bundle_items()
    print(f"Se encontraron {len(bundles)} bundles.")

    # 3. Preparar CSV
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Game Name", "URL", "Price", "Reviews", "Categories",
            "Game Label", "Release Date", "Editor", "Developer"
        ])

        # 4. Iterar sobre cada bundle
        for idx, bundle in enumerate(bundles, start=1):
            print(f"\n📌 [{idx}/{len(bundles)}] Procesando bundle...")

            try:
                # Clic en el bundle
                bundle.click()
                page.wait_for_load_state("networkidle")

                # Buscar y abrir enlace de Steam
                result = home_page.click_view_on_steam_button(idx)

                # Si no es bundle ni juego con Steam
                if result is False:
                    print(f"[{idx}] No se encontró enlace de Steam.")
                    page.goto(home_page.page.url)
                    home_page.handle_popups()
                    continue

                # Si es bundle (lista de dicts), guardar datos directamente
                if isinstance(result, list):
                    print(f"[{idx}] Bundle con {len(result)} juegos.")
                    for game_data in result:
                        row = [
                            game_data.get("game_name", "N/A"),
                            game_data.get("url", "N/A"),
                            game_data.get("price", "N/A"),
                            game_data.get("reviews", "N/A"),
                            game_data.get("categories", "N/A"),
                            game_data.get("game_label", "N/A"),
                            game_data.get("release_date", "N/A"),
                            game_data.get("editor", "N/A"),
                            game_data.get("developer", "N/A"),
                        ]
                        writer.writerow(row)
                        print(f"[{idx}] Datos de bundle guardados: {game_data.get('game_name')}")

                    # Volver a Fanatical
                    home_page.open_home()
                    home_page.handle_popups()
                    continue

                # Si es juego individual (True) → capturar popup de Steam
                print(f"[{idx}] Juego individual, capturando popup de Steam...")

                with page.expect_popup(timeout=10000) as popup_info:
                    pass  # La popup ya se abrió en click_view_on_steam_button

                steam_page_obj = popup_info.value
                steam_page_obj.wait_for_load_state("networkidle")

                steam_page = SteamGamePage(steam_page_obj)
                steam_page.handle_initial_overlays()

                # Extraer datos
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

                print(f"[{idx}] ✅ Datos guardados: {row[0]}")

                # Cerrar pestaña de Steam y volver a Fanatical
                steam_page_obj.close()

            except Exception as e:
                print(f"[{idx}] ❌ Error procesando bundle: {e}")
                # Intentar cerrar popups y volver a Fanatical
                try:
                    for p in page.context.pages:
                        if p != page:
                            p.close()
                except Exception:
                    pass
                home_page.open_home()
                home_page.handle_popups()

    # 5. Leer y mostrar CSV generado
    print(f"\n{'='*70}")
    print(f"📊 CONTENIDO DEL CSV: {csv_filename}")
    print(f"{'='*70}")
    with open(csv_filename, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            print(row)

    print(f"\n✅ Reporte generado: {csv_filename}")