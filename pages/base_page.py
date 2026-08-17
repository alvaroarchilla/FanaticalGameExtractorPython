"""
Archivo: pages/base_page.py
Descripción: Clase base para todas las páginas del proyecto (Playwright).
"""

from playwright.sync_api import Page, Locator, expect


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    # ── Navegación ──────────────────────────────────────────────────────────

    def open(self, url: str):
        self.page.goto(url, wait_until="domcontentloaded")

    def click_stable(self, locator: str | Locator, timeout: float = 10000):
        """Click resistente a animaciones (scroll + force)."""
        element = self._resolve_locator(locator)
        element.scroll_into_view_if_needed()
        try:
            element.click(timeout=timeout)
        except Exception:
            element.click(force=True, timeout=timeout)

    # ── Clicks ──────────────────────────────────────────────────────────────

    def click(self, locator: str | Locator):
        """
        Hace click en un elemento.
        Acepta selector CSS/XPath (str) o un Locator de Playwright.
        """
        element = self._resolve_locator(locator)
        element.click()

    def click_force(self, locator: str | Locator):
        """Hace click forzando con JavaScript (útil para elementos ocultos)."""
        element = self._resolve_locator(locator)
        element.evaluate("el => el.click()")

    # ── Texto ───────────────────────────────────────────────────────────────

    def get_text(self, locator: str | Locator) -> str:
        """Obtiene el texto visible de un elemento."""
        element = self._resolve_locator(locator)
        return element.text_content() or ""

    def get_inner_text(self, locator: str | Locator) -> str:
        """Obtiene el innerText (solo texto visible, sin hidden)."""
        element = self._resolve_locator(locator)
        return element.inner_text()

    # ── Formularios ─────────────────────────────────────────────────────────

    def write(self, locator: str | Locator, text: str):
        """Limpia el campo y escribe texto."""
        element = self._resolve_locator(locator)
        element.fill(text)

    def clear_and_type(self, locator: str | Locator, text: str):
        """Limpia, escribe y dispara eventos de input (alternativa a fill)."""
        element = self._resolve_locator(locator)
        element.clear()
        element.type(text)

    # ── Presencia y visibilidad ─────────────────────────────────────────────

    def is_element_present(self, locator: str | Locator, timeout: float = 2.0) -> bool:
        """Devuelve True si el elemento está presente en el DOM."""
        try:
            element = self._resolve_locator(locator)
            element.wait_for(state="attached", timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def is_visible(self, locator: str | Locator, timeout: float = 2.0) -> bool:
        """Devuelve True si el elemento es visible."""
        try:
            element = self._resolve_locator(locator)
            element.wait_for(state="visible", timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def is_clickable(self, locator: str | Locator, timeout: float = 2.0) -> bool:
        """Devuelve True si el elemento es clicable."""
        try:
            element = self._resolve_locator(locator)
            element.wait_for(state="visible", timeout=timeout * 1000)
            return element.is_enabled()
        except Exception:
            return False

    # ── Esperas ─────────────────────────────────────────────────────────────

    def wait_for_element(self, locator: str | Locator, timeout: float = 10.0):
        """Espera a que el elemento esté presente en el DOM."""
        element = self._resolve_locator(locator)
        element.wait_for(state="attached", timeout=timeout * 1000)

    def wait_for_visible(self, locator: str | Locator, timeout: float = 10.0):
        """Espera a que el elemento sea visible."""
        element = self._resolve_locator(locator)
        element.wait_for(state="visible", timeout=timeout * 1000)

    def wait_for_hidden(self, locator: str | Locator, timeout: float = 10.0):
        """Espera a que el elemento desaparezca."""
        element = self._resolve_locator(locator)
        element.wait_for(state="hidden", timeout=timeout * 1000)

    def wait_for_load(self):
        """Espera a que el DOM principal esté listo."""
        self.page.wait_for_load_state("domcontentloaded")

    # ── Utilidades ──────────────────────────────────────────────────────────

    def get_attribute(self, locator: str | Locator, attribute: str) -> str | None:
        """Obtiene un atributo de un elemento."""
        element = self._resolve_locator(locator)
        return element.get_attribute(attribute)

    def scroll_to(self, locator: str | Locator):
        """Hace scroll hasta un elemento."""
        element = self._resolve_locator(locator)
        element.scroll_into_view_if_needed()

    # ── Helpers privados ────────────────────────────────────────────────────

    def _resolve_locator(self, locator: str | Locator) -> Locator:
        """
        Convierte un string (selector CSS/XPath) en un Locator de Playwright.
        Si ya es un Locator, lo devuelve tal cual.
        """
        if isinstance(locator, Locator):
            return locator
        return self.page.locator(locator)