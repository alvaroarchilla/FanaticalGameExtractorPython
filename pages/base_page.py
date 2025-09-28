# Clase base para todas las páginas
"""
Archivo: pages/base_page.py
Descripción: Clase base para todas las páginas del proyecto.
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def open(self, url):
        self.driver.get(url)

    def click(self, locator):
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.click()

    def get_text(self, locator):
        element = self.wait.until(EC.visibility_of_element_located(locator))
        return element.text

    def is_element_present(self, locator):
        """Devuelve True si el elemento está presente en el DOM."""
        try:
            self.driver.find_element(*locator)
            return True
        except:
            return False

    def is_clickable(self, locator):
        """Devuelve True si el elemento es clicable."""
        try:
            self.wait.until(EC.element_to_be_clickable(locator))
            return True
        except:
            return False
