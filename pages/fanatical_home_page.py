"""
Archivo: pages/fanatical_home_page.py
Descripción: Representa la página principal de Fanatical con sus elementos y acciones.
"""

from selenium.webdriver.common.by import By
from pages.base_page import BasePage
from config.settings import FANATICAL_URL
import time
class FanaticalHomePage(BasePage):
    # ===== Localizadores =====
    ALLOW_ALERT = (By.XPATH, "//*[@id='root']/div/section/div/div/div/button[1]")
    GAMES_CATEGORY = (By.XPATH, "//*[@id='root']/div/div[2]/div/div/nav/div/a[2]")
    EBOOKS_CATEGORY = (By.XPATH, "//*[@id='root']/div/div[2]/div/div/nav/div/a[3]")
    SOFTWARE_CATEGORY = (By.XPATH, "//*[@id='root']/div/div[2]/div/div/nav/div/a[4]")
    AUDIO_CATEGORY = (By.XPATH, "//*[@id='root']/div/div[2]/div/div/nav/div/a[5]")

    CLOSE_NEWSLETTER = (By.XPATH, "//*[@id='lightbox-cb4fd363-c404-47cc-926e-16a282f0636e-1647367590861']/div")
    CLOSE_COOKIES = (By.CLASS_NAME, "accept-cookies-btn")

    BUNDLE_ITEM_LOCATOR = (By.XPATH, "//*[@id='root']/div/div/div/div/div/div/div/div/div/div/div[2]")
    BUNDLE_ITEM_LOCATOR2 = (By.XPATH, "//*[@id='root']/div/div/div/div/div[2]/div/div")

    NEXT_ITEM_BUTTON = (
    By.XPATH, "//*[@id='root']/div/div[2]/main/div[3]/section[1]/div[1]/div[1]/div/div[2]/button[2]")
    WEB_ITEMS = (By.XPATH, "//*[@id='root']/div/div/main/div/section/section/div/article")
    FIRST_ITEM = (By.XPATH, "//*[@id='root']/div/div[2]/main/div[2]/section/section/div[1]/article")
    VIEW_ON_STEAM = (By.LINK_TEXT, "View on Steam")
    VIEW = (By.LINK_TEXT, "VIEW")

    # ===== Acciones =====
    def open_home(self):
        """Abre la página principal de Fanatical."""
        self.open(FANATICAL_URL)

    def accept_alert_if_present(self):
        """Acepta el aviso inicial si aparece, sin esperas largas."""
        elems = self.driver.find_elements(*self.ALLOW_ALERT)
        if elems:
            try:
                elems[0].click()
                print("Clicking on Accept Alert.")
            except Exception:
                pass  # Ignorar si no se puede hacer clic

    def close_newsletter_if_present(self):
        """Cierra el pop-up de newsletter si aparece, sin esperas largas."""
        elems = self.driver.find_elements(*self.CLOSE_NEWSLETTER)
        if elems:
            try:
                elems[0].click()
                print("Clicking on Close Newsletter.")
            except Exception:
                pass

    def accept_cookies_if_present(self):
        """Acepta cookies si aparece el botón, sin esperas largas."""
        elems = self.driver.find_elements(*self.CLOSE_COOKIES)
        if elems:
            try:
                elems[0].click()
                print("Clicking on Close Cookies.")
            except Exception:
                pass

    def handle_popups(self):
        """Ejecuta las acciones iniciales para cerrar alertas, newsletter y aceptar cookies si están presentes."""
        self.accept_alert_if_present()
        self.close_newsletter_if_present()
        self.accept_cookies_if_present()

    def go_to_games_category(self):
        """Navega a la categoría de juegos."""
        self.click(self.GAMES_CATEGORY)

    def go_to_ebooks_category(self):
        """Navega a la categoría de ebooks."""
        self.click(self.EBOOKS_CATEGORY)

    def go_to_software_category(self):
        """Navega a la categoría de software."""
        self.click(self.SOFTWARE_CATEGORY)

    def go_to_audio_category(self):
        """Navega a la categoría de audio."""
        self.click(self.AUDIO_CATEGORY)

    def get_bundle_items(self):
        """
        Devuelve una lista de elementos que representan los bundles.
        Nota: Aquí podrías combinar BUNDLE_ITEM_LOCATOR y BUNDLE_ITEM_LOCATOR2 según la página.
        """
        items = []
        try:
            items.extend(self.driver.find_elements(*self.WEB_ITEMS))
            self.driver.find_elements(*self.WEB_ITEMS)
        except Exception:
            pass
        try:
            items.extend(self.driver.find_elements(*self.BUNDLE_ITEM_LOCATOR2))
        except Exception:
            pass
        return items



    def open_home(self):
        self.open(FANATICAL_URL)

    def click_view_on_steam_button(self, idx=None) -> bool:
        """
        Intenta hacer clic en el enlace de Steam.
        Devuelve True si se hizo clic en VIEW_ON_STEAM o VIEW,
        False si no se encontró ninguno.
        """
        try:
            if self.is_element_present(self.VIEW_ON_STEAM):
                self.click(self.VIEW_ON_STEAM)
                return True
            elif self.is_element_present(self.VIEW):
                self.click(self.VIEW)
                return True
            else:
                msg = f"[{idx}] No se encontró enlace de Steam." if idx else "No se encontró enlace de Steam."
                print(msg)
                self.click(self.NEXT_ITEM_BUTTON)
                time.sleep(0.5)
                return False
        except Exception as e:
            print(f"[{idx}] Error con el botón ViewOnSteam: {e}" if idx else f"Error con el botón ViewOnSteam: {e}")
            return False

    def steam_data_extraction(self):
        """
        Reproduce el comportamiento del método Java steamDataExtractionToHTML().
        - Abre el primer ítem.
        - Itera sobre todos los ítems.
        - Si encuentra enlaces 'View on Steam' o 'VIEW', los abre.
        - Pasa al siguiente ítem con el botón 'next'.
        """
        # Obtener lista de elementos
        web_items = self.driver.find_elements(*self.WEB_ITEMS)

        # Abrir el primer ítem
        try:
            self.click(self.FIRST_ITEM)
        except Exception as e:
            print("No se pudo hacer clic en el primer ítem:", e)
            return

        # Iterar sobre todos los ítems
        for _ in web_items:
            try:
                if self.is_element_present(self.VIEW_ON_STEAM):
                    self.click(self.VIEW_ON_STEAM)

                if self.is_element_present(self.VIEW):
                    self.click(self.VIEW)

                # Ir al siguiente ítem
                self.click(self.NEXT_ITEM_BUTTON)

            except Exception as e:
                print("Ocurrió un error en la iteración:", e)

    def is_element_present(self, locator):
        """Devuelve True si el elemento está presente en el DOM."""
        try:
            self.driver.find_element(*locator)
            return True
        except:
            return False