"""Helpers compartidos para el listado de pick-and-mix de Fanatical."""
from playwright.sync_api import Page

from pages.fanatical_home_page import FanaticalHomePage

BASE_URL = "https://www.fanatical.com"
BUNDLES_LIST_URL = f"{BASE_URL}/en/bundle/games"


def dismiss_language_banner(page: Page) -> None:
    """Mantener inglés si aparece el banner de idioma."""
    try:
        btn = page.locator("button:has-text('permanecer')").first
        if btn.is_visible(timeout=1500):
            btn.click(timeout=2000)
    except Exception:
        pass


def collect_pick_and_mix_urls(page: Page) -> list[str]:
    """URLs absolutas de pick-and-mix visibles en el listado (HitCards)."""
    home = FanaticalHomePage(page)
    home.handle_popups()
    dismiss_language_banner(page)

    page.wait_for_selector("a.HitCard__main__cover", state="attached", timeout=30000)

    prev = 0
    for _ in range(10):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(600)
        n = page.locator("a.HitCard__main__cover").count()
        if n == prev:
            break
        prev = n

    hrefs = page.eval_on_selector_all(
        "a.HitCard__main__cover",
        """els => [...new Set(
            els.map(e => (e.getAttribute('href') || '').split('?')[0])
               .filter(h => h.includes('/pick-and-mix/'))
        )]""",
    )

    absolute = []
    for href in hrefs:
        if href.startswith("http"):
            absolute.append(href)
        else:
            absolute.append(f"{BASE_URL}{href}")
    return absolute
