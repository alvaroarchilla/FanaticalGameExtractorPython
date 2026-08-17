from playwright.sync_api import Page, Locator
from pages.base_page import BasePage
from config.settings import FANATICAL_URL


class FanaticalHomePage(BasePage):
    # ===== Localizadores =====
    ALLOW_ALERT = "//*[@id='root']/div/section/div/div/div/button[1]"
    CLOSE_NEWSLETTER = "//*[@id='lightbox-cb4fd363-c404-47cc-926e-16a282f0636e-1647367590861']/div"
    CLOSE_COOKIES = ".accept-cookies-btn"
    WEB_ITEMS = "article.PickAndMixCard"
    DETAIL_PANEL = ".product-details, .inline-bundle-section"
    VIEW_ON_STEAM = (
        ".product-details:visible a[href*='store.steampowered.com'], "
        ".inline-bundle-section:visible a[href*='store.steampowered.com']"
    )
    VIEW = ".product-details:visible a:has-text('VIEW'):not(:has-text('View on Steam'))"
    BUNDLE_HEADER = (
        ".product-details:visible h4:has-text('This bundle includes:'), "
        ".inline-bundle-section:visible h4:has-text('This bundle includes:')"
    )
    BUNDLE_ITEMS = (
        ".product-details:visible h4:has-text('This bundle includes:') + ul > li, "
        ".inline-bundle-section:visible h4:has-text('This bundle includes:') + ul > li"
    )

    def __init__(self, page: Page):
        super().__init__(page)

    def open_home(self):
        self.open(FANATICAL_URL)

    def accept_alert_if_present(self):
        try:
            alert = self.page.locator(self.ALLOW_ALERT).first
            if alert.is_visible(timeout=1500):
                print("[Fanatical] Cerrando alerta de bienvenida")
                alert.click(timeout=2000)
        except Exception:
            pass

    def close_newsletter_if_present(self):
        try:
            modal = self.page.locator(self.CLOSE_NEWSLETTER).first
            if modal.is_visible(timeout=800):
                print("[Fanatical] Cerrando newsletter")
                modal.click(timeout=2000)
        except Exception:
            pass

    def accept_cookies_if_present(self):
        try:
            btn = self.page.locator(self.CLOSE_COOKIES).first
            if btn.is_visible(timeout=2000):
                print("[Fanatical] Aceptando cookies")
                btn.click(timeout=2000)
                try:
                    btn.wait_for(state="hidden", timeout=3000)
                except Exception:
                    pass
        except Exception:
            pass

    def handle_popups(self):
        print("[Fanatical] Manejando popups...")
        self.accept_alert_if_present()
        self.close_newsletter_if_present()
        self.accept_cookies_if_present()
        print("[Fanatical] Popups manejados")

    def get_bundle_items(self) -> list[Locator]:
        print("[Fanatical] Buscando webitems...")
        items_locator = self.page.locator(self.WEB_ITEMS)
        items_locator.first.wait_for(state="visible", timeout=15000)
        items = items_locator.all()
        print(f"[Fanatical] Encontrados {len(items)} webitems")
        return items

    def wait_for_product_grid(self, timeout: float = 15000):
        self.page.locator(self.WEB_ITEMS).first.wait_for(state="visible", timeout=timeout)

    def get_bundle_tiers(self) -> dict:
        """
        Extrae el mensaje de ahorro y los tiers de precio del aside.
        Devuelve: {summary: str, tiers: [{quantity, price, per_item}, ...]}
        """
        result = {"summary": "", "tiers": []}
        try:
            # Esperar a que el aside/tiers estén en el DOM
            try:
                self.page.locator(
                    ".PickAndMixTierBox, .PickAndMixProductPage__content__saveMoreMessage"
                ).first.wait_for(state="attached", timeout=10000)
            except Exception:
                pass

            summary = self.page.locator(
                ".PickAndMixProductPage__content__saveMoreMessage"
            ).first
            if summary.count() > 0:
                result["summary"] = " ".join(summary.inner_text().split())

            boxes = self.page.locator(".PickAndMixTierBox")
            for i in range(boxes.count()):
                box = boxes.nth(i)
                qty = ""
                price = ""
                per_item = "Per item"
                try:
                    qty_el = box.locator(".PickAndMixTierBox__quantity")
                    if qty_el.count():
                        qty = " ".join(qty_el.first.inner_text().split())
                except Exception:
                    pass
                try:
                    price_spans = box.locator(".PickAndMixTierBox__price > span")
                    if price_spans.count() > 0:
                        price = " ".join(price_spans.first.inner_text().split())
                    per_el = box.locator(".PickAndMixTierBox__price__perItem")
                    texts = []
                    for j in range(per_el.count()):
                        t = " ".join(per_el.nth(j).inner_text().split())
                        if t and t != "/":
                            texts.append(t)
                    if texts:
                        per_item = texts[-1]
                except Exception:
                    pass
                if qty or price:
                    result["tiers"].append({
                        "quantity": qty,
                        "price": price,
                        "per_item": per_item,
                    })
        except Exception as e:
            print(f"[Fanatical] No se pudieron leer los tiers: {e}")

        if result["tiers"]:
            print(f"[Fanatical] Tiers encontrados: {len(result['tiers'])}")
        else:
            print("[Fanatical] No se encontraron tiers de precio")
        return result

    def _card_title(self, idx: int) -> str:
        card = self.page.locator(self.WEB_ITEMS).nth(idx)
        for sel in ("h3", "h2", "h4"):
            loc = card.locator(sel)
            if loc.count() > 0:
                text = loc.first.inner_text().strip()
                if text:
                    return text
        return (card.inner_text() or "").strip().split("\n")[0]

    def _normalize_steam_href(self, href: str | None) -> str | None:
        if not href or "store.steampowered.com" not in href:
            return None
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("http://"):
            href = "https://" + href[len("http://"):]
        return href

    def get_steam_href(self) -> str | None:
        link = self.page.locator(self.VIEW_ON_STEAM).first
        try:
            if link.count() == 0:
                return None
            return self._normalize_steam_href(link.get_attribute("href"))
        except Exception:
            return None

    def _is_bundle_visible(self) -> bool:
        try:
            return self.page.locator(self.BUNDLE_HEADER).first.is_visible(timeout=500)
        except Exception:
            return False

    def _is_sold_out(self, idx: int) -> bool:
        card = self.page.locator(self.WEB_ITEMS).nth(idx)
        try:
            cls = (card.get_attribute("class") or "").lower()
            if "sold-out" in cls or "soldout" in cls:
                return True
            text = (card.inner_text() or "").lower()
            return "sold out" in text
        except Exception:
            return False

    def open_webitem(self, idx: int, expected_title: str | None = None):
        """Abre la card del grid y espera a que el detalle muestre ese producto."""
        item = self.page.locator(self.WEB_ITEMS).nth(idx)
        item.scroll_into_view_if_needed()
        title = expected_title or self._card_title(idx)
        frag = title.split(":")[0].strip()
        if len(frag) > 40:
            frag = frag[:40]
        frag_lower = frag.lower()
        previous_href = self.get_steam_href()

        for attempt in range(3):
            # Click en zona izquierda de la card (evita solapamiento con el panel)
            try:
                item.click(position={"x": 40, "y": 40}, force=True, timeout=5000)
            except Exception:
                try:
                    item.evaluate("el => el.click()")
                except Exception:
                    item.locator("img, h3, h2").first.click(force=True, timeout=5000)

            try:
                self.page.wait_for_function(
                    """(frag) => {
                        const nodes = document.querySelectorAll(
                            '.product-details, .inline-bundle-section'
                        );
                        for (const n of nodes) {
                            if (!n) continue;
                            const text = (n.innerText || '').toLowerCase();
                            const alts = Array.from(n.querySelectorAll('img[alt]'))
                                .map(img => (img.getAttribute('alt') || '').toLowerCase())
                                .join(' ');
                            if (text.includes(frag) || alts.includes(frag)) return true;
                        }
                        return false;
                    }""",
                    arg=frag_lower,
                    timeout=5000,
                )
                return
            except Exception:
                href_now = self.get_steam_href()
                if href_now and href_now != previous_href:
                    return
                print(f"[Fanatical] Reintento abrir card {idx} ({title})")
                self.page.wait_for_timeout(200)

        raise TimeoutError(f"No se pudo abrir el detalle de '{title}' (idx={idx})")

    def collect_jobs(self) -> list[dict]:
        """
        Recorre el grid de Fanatical SIN abrir Steam.
        Devuelve trabajos: {type: 'steam'|'bundle'|'search', title, steam_url?, game_names?}
        """
        cards = self.get_bundle_items()
        jobs: list[dict] = []

        for idx in range(len(cards)):
            title = self._card_title(idx)
            print(f"[Fanatical] [{idx}] Abriendo: {title}")

            # Agotados: no abren panel de detalle; se buscan luego en Steam
            if self._is_sold_out(idx):
                print(f"[Fanatical] [{idx}] SOLD OUT -> busqueda por nombre en Steam")
                jobs.append({"type": "search", "title": title})
                continue

            try:
                self.open_webitem(idx, expected_title=title)
            except TimeoutError as e:
                print(f"[Fanatical] [{idx}] {e} -> se buscara por nombre en Steam")
                jobs.append({"type": "search", "title": title})
                continue

            if self._is_bundle_visible():
                names = []
                try:
                    lis = self.page.locator(self.BUNDLE_ITEMS)
                    count = lis.count()
                    for i in range(count):
                        name = (lis.nth(i).inner_text(timeout=3000) or "").strip()
                        if name:
                            names.append(name)
                except Exception as e:
                    print(f"[Fanatical] [{idx}] Error leyendo bundle: {e}")
                print(f"[Fanatical] [{idx}] Bundle con {len(names)} juegos")
                if names:
                    jobs.append({
                        "type": "bundle",
                        "title": title,
                        "game_names": names,
                    })
                else:
                    jobs.append({"type": "search", "title": title})
                continue

            href = self.get_steam_href()
            if href:
                print(f"[Fanatical] [{idx}] Steam: {href}")
                jobs.append({
                    "type": "steam",
                    "title": title,
                    "steam_url": href,
                })
                continue

            print(f"[Fanatical] [{idx}] Sin Steam ni bundle -> busqueda por nombre")
            jobs.append({"type": "search", "title": title})

        return jobs

    # Compatibilidad con flujos antiguos
    def click_view_on_steam_button(self, idx: int | None = None) -> list[dict] | str | bool:
        if self._is_bundle_visible():
            names = []
            for li in self.page.locator(self.BUNDLE_ITEMS).all():
                name = (li.text_content() or "").strip()
                if name:
                    names.append(name)
            return [{"game_name": n} for n in names]

        href = self.get_steam_href()
        if href:
            return href
        return False
