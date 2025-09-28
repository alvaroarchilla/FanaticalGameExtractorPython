import pytest
import time
from selenium.webdriver.common.by import By
from utils.driver_factory import create_driver
from tests.utils_html_report import generar_html_desde_url

@pytest.fixture
def driver():
    driver = create_driver()
    yield driver
    driver.quit()

def test_all_bundles(driver):
    # 1. Ir a la página de todos los bundles
    driver.get("https://www.fanatical.com/en/bundle/games")
    time.sleep(1)

    # 2. Obtener todos los enlaces de bundles
    bundle_elements = driver.find_elements(By.XPATH, '//*[@id="root"]/div/div[2]/div/div[2]/ul/li/div/div/a')
    bundle_urls = [el.get_attribute("href") for el in bundle_elements if el.get_attribute("href")]

    print(f"Encontrados {len(bundle_urls)} bundles.")

    # 3. Procesar cada bundle individualmente
    for url in bundle_urls:
        print(f"\n--- Procesando bundle: {url} ---")
        generar_html_desde_url(driver, url)
