from selenium.webdriver.common.by import By
from pages.base_page import BasePage
from enum import Enum
import time
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
class SteamGamePageData(Enum):
    GAME_NAME = "game_name"
    URL = "url"
    PRICE = "price"
    REVIEWS = "reviews"
    CATEGORIES = "categories"
    GAME_LABEL = "game_label"
    RELEASE_DATE = "release_date"
    EDITOR = "editor"
    DEVELOPER = "developer"

class SteamGamePage(BasePage):
    # ===== Localizadores =====
    CATEGORY_ELEMENT = (By.XPATH, "//*[@id='category_block']/div/a")
    PRICE_ELEMENT = (By.XPATH, "//div[@class='game_purchase_price price' and not(ancestor::div[@id='dlc_purchase_action'])]")
    PRICE_DISCOUNTED_ELEMENT = (By.CLASS_NAME, "discount_final_price")
    GAME_LABEL = (By.XPATH, "//*[@id='app_tagging_modal']/div/div[2]/div/div/a")
    GAME_NAME = (By.XPATH, "//*[@id='appHubAppName']")
    GAME_RELEASE_DATE = (By.XPATH, "//div[@class='release_date']/div[@class='date']")
    GAME_DEVELOPER_NAME = (By.XPATH, "//*[@id='developers_list']")
    GAME_EDITOR_NAME = (By.XPATH, "//div[contains(@class,'dev_row')]//div[@class='summary column' and not(@id='developers_list')]")
    REVIEW_GENERAL = (By.XPATH, "//*[@id='userReviews']/a[2]")
    MODAL_CATEGORY_LOCATOR = (By.XPATH, "//*[@id='app_tagging_modal']/div/div[2]/div/div/a")
    REJECT_COOKIES_BUTTON = (By.ID, "rejectAllButton")  # Ejemplo, cambia por el real
    NOT_AUTHORISED_BUTTON = (By.ID, "notAuthorisedButton")  # Ejemplo, cambia por el real
    AGE_YEAR_SELECT = (By.ID, "ageYear")
    AGE_SUBMIT_BUTTON = (By.CLASS_NAME, "btnv6_blue_hoverfade.btn_medium")
    TAG_BUTTON = (By.XPATH, "//*[@id='glanceCtnResponsiveRight']/div[2]/div[2]/div")
    HIDE_LIVE_BROADCAST_BUTTON = (By.XPATH,"//*[@id='game_highlights']/div[1]/div/div[1]/div[1]/div[3]")

    # ===== Métodos de obtención de datos =====
    def get_game_name(self):
        print(f"GameName: {self.get_text(self.GAME_NAME)}")
        return self.get_text(self.GAME_NAME)

    def get_price(self):
        try:
            return self.get_text(self.PRICE_ELEMENT)
        except:
            return self.get_text(self.PRICE_DISCOUNTED_ELEMENT)

    def get_reviews(self):
        """Devuelve un string con el texto de todas las reseñas encontradas dentro de #userReviews."""
        reviews = []
        try:
            # Esperar a que exista el contenedor
            container = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "userReviews"))
            )
            links = container.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    # Buscar el span[3] dentro del segundo div
                    span_elem = link.find_element(By.XPATH, ".//div[2]/span[3]")
                    text_value = span_elem.get_attribute("textContent").strip()
                    print(f"Text value: {text_value}")
                    if text_value:
                        reviews.append(text_value)
                    time.sleep(0.5)
                except NoSuchElementException:
                    continue  # Si este enlace no tiene span[3], probamos con el siguiente

        except NoSuchElementException:
            pass

        # Devolver todos los textos concatenados con " | " o lista según prefieras
        return "\n".join(reviews) if reviews else ""

    def get_categories(self):
        return ", ".join([el.text.strip() for el in self.driver.find_elements(*self.CATEGORY_ELEMENT)])

    def get_game_label(self):
        """Hace clic en el botón de etiquetas del juego si está presente y clicable y devuelve la lista de tags."""
        try:
            if self.is_clickable(self.TAG_BUTTON):
                #("Clicking GAME TAG BUTTON")
                self.driver.find_element(*self.TAG_BUTTON).click()
                # Pequeña espera para que se desplieguen las etiquetas
                time.sleep(0.5)
                # Obtener lista de etiquetas como lista de strings
                elements = self.driver.find_elements(*self.GAME_LABEL)
                tags = [el.text.strip() for el in elements if el.text.strip()]
                return tags
        except Exception as e:
            print("An error occurred in get_game_label()")
            print(e)
        return

    def get_release_date(self):
        return self.get_text(self.GAME_RELEASE_DATE)

    def get_editor(self):
        return self.get_text(self.GAME_EDITOR_NAME)

    def get_developer(self):
        return self.get_text(self.GAME_DEVELOPER_NAME)

    def get_url(self):
        return self.driver.current_url

    # ===== Método genérico =====
    def click_reject_cookies_steam(self):
        elems = self.driver.find_elements(*self.REJECT_COOKIES_BUTTON)
        if elems:
            """Hace clic en el botón de rechazar cookies si está presente y clicable."""
            try:
                if self.is_clickable(self.REJECT_COOKIES_BUTTON):
                    print("Clicking RejectCookiesButton")
                    self.driver.find_element(*self.REJECT_COOKIES_BUTTON).click()
            except Exception as e:
                print("An error occurred in click_reject_cookies_steam.")
                print(e)

    def click_not_authorised_button(self):
        elems = self.driver.find_elements(*self.HIDE_LIVE_BROADCAST_BUTTON)
        if elems:
            """Hace clic en el botón 'Not Authorised' si está presente y recarga la página."""
            try:
                if self.is_element_present(self.NOT_AUTHORISED_BUTTON):
                    if self.is_clickable(self.NOT_AUTHORISED_BUTTON):
                        print("Clicking NotAuthorisedButton")
                        self.driver.find_element(*self.NOT_AUTHORISED_BUTTON).click()
                        self.driver.refresh()
            except Exception as e:
                print("An error occurred in click_not_authorised_button.")
                print(e)

    def click_hide_live_stream(self, timeout=3):
        elems = self.driver.find_elements(*self.AGE_YEAR_SELECT)
        if elems:
            """Espera hasta que el botón de ocultar live stream sea clicable y hace clic."""
            try:
                button = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable(self.HIDE_LIVE_BROADCAST_BUTTON)
                )
                print("Hiding Live Broadcast")
                button.click()
            except Exception as e:
                # Si no aparece o no se puede clicar en el tiempo dado, seguimos sin error
                print("Live Broadcast no estaba presente o no fue clicable a tiempo.")

    def accept_age_child_control(self):
        elems = self.driver.find_elements(*self.AGE_YEAR_SELECT)
        if elems:
            """Selecciona un año de nacimiento (1970) y envía el formulario de control de edad."""
            try:
                if self.is_element_present(self.AGE_YEAR_SELECT):
                    print("Clicking on age_child_control.")
                    self.driver.find_element(*self.AGE_YEAR_SELECT).click()
                    dropdown = self.driver.find_element(*self.AGE_YEAR_SELECT)
                    dropdown.find_element(By.XPATH, "//option[. = '1970']").click()
                    self.driver.find_element(*self.AGE_SUBMIT_BUTTON).click()
            except Exception as e:
                print("An error occurred in age_child_control.")
                print(e)

    def handle_initial_overlays(self):
        """Ejecuta las acciones iniciales para limpiar la interfaz de Steam sin mostrar errores si los elementos no están presentes."""
        self.accept_age_child_control()
        self.click_reject_cookies_steam()
        self.click_hide_live_stream()
        self.click_not_authorised_button()

    def get_generic_data(self, selected_data: SteamGamePageData):
        """
        Devuelve el dato solicitado según el tipo de SteamGamePageData.
        """
        try:
            mapping = {
                SteamGamePageData.GAME_NAME: self.get_game_name,
                SteamGamePageData.PRICE: self.get_price,
                SteamGamePageData.REVIEWS: self.get_reviews,
                SteamGamePageData.CATEGORIES: self.get_categories,
                SteamGamePageData.GAME_LABEL: self.get_game_label,
                SteamGamePageData.RELEASE_DATE: self.get_release_date,
                SteamGamePageData.EDITOR: self.get_editor,
                SteamGamePageData.DEVELOPER: self.get_developer,
                SteamGamePageData.URL: self.get_url
            }
            return mapping[selected_data]()
        except Exception:
            return f"Cannot retrieve '{selected_data.name}' info from steam game!"

    # ===== Mostrar todos los datos =====
    def show_all_game_data(self):
        """
        Devuelve un string concatenando varios datos clave del juego.
        """
        datastring = ""
        datastring += self.get_game_name() + " | "
        datastring += self.get_price() + " | "
        datastring += self.get_categories() + " | "
        datastring += self.get_game_label()
        print(datastring)
        return datastring
