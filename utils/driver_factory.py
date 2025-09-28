# Inicialización de WebDriver

"""
Archivo: utils/driver_factory.py
Descripción: Fábrica de WebDriver para inicializar navegadores.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from config import settings

def create_driver():
    """
    Crea e inicializa el WebDriver según la configuración.
    """
    if settings.BROWSER.lower() == "chrome":
        options = webdriver.ChromeOptions()
        if settings.START_MAXIMIZED:
            options.add_argument("--start-maximized")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    else:
        raise ValueError(f"Navegador no soportado: {settings.BROWSER}")
