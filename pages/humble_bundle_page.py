"""Page Object para listados y fichas de bundles de Humble Bundle."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode

from playwright.sync_api import Page

from pages.base_page import BasePage

BASE_URL = "https://www.humblebundle.com"
GAMES_LIST_URL = f"{BASE_URL}/games"

_SKIP_TITLE_RE = re.compile(
    r"(soundtrack|\bost\b|coupon|wallpaper|artbook|art book|ebook|pdf|"
    r"manual|avatar|theme|dlc\s*only|\d+\s*%\s*off|%\s*off)",
    re.IGNORECASE,
)


class HumbleBundlePage(BasePage):
    COOKIE_ACCEPT = (
        "button:has-text('Accept'), #onetrust-accept-btn-handler, "
        "button:has-text('Aceptar todo'), button:has-text('Accept All')"
    )
    BUNDLE_TILE_LINKS = (
        'a[href*="/games/"][href*="hmb_medium=product_tile"], '
        'a[href^="/games/"]'
    )
    TIER_HEADER = "h3.tier-header, .js-tier-header"
    ITEM_VIEW = ".tier-item-view"
    ITEM_TITLE = ".item-title"
    ITEM_IMAGE = "img.item-image"
    DETAILS_VIEW = ".tier-item-details-view"
    BUNDLE_TITLE = "h1.heading-large .bundle-logo, h1.heading-large, .bundle-title h1"

    def __init__(self, page: Page):
        super().__init__(page)

    def handle_popups(self):
        print("[Humble] Manejando popups...")
        try:
            btn = self.page.locator(self.COOKIE_ACCEPT).first
            if btn.is_visible(timeout=2500):
                btn.click(timeout=3000)
                self.page.wait_for_timeout(500)
        except Exception:
            pass
        print("[Humble] Popups manejados")

    @staticmethod
    def _clean_url(href: str) -> str:
        if not href:
            return ""
        absolute = href if href.startswith("http") else urljoin(BASE_URL, href)
        parsed = urlparse(absolute)
        # Quitar tracking params
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    def collect_bundle_urls(self) -> list[str]:
        """URLs únicas de bundles de juegos en /games."""
        self.page.wait_for_selector('a[href*="/games/"]', state="attached", timeout=30000)
        self.page.wait_for_timeout(1500)

        hrefs = self.page.eval_on_selector_all(
            'a[href*="/games/"]',
            """els => [...new Set(
                els.map(e => (e.getAttribute('href') || '').split('?')[0])
                   .filter(h => h && h.includes('/games/') && h !== '/games'
                                && !h.includes('/store') && !h.includes('/category'))
            )]""",
        )
        # Filtrar rutas que no son bundles concretos (muy cortas / genéricas)
        urls = []
        seen = set()
        for h in hrefs:
            path = h if h.startswith("http") else urljoin(BASE_URL, h)
            clean = self._clean_url(path)
            # /games/<slug> con slug real
            m = re.search(r"/games/([^/]+)/?$", urlparse(clean).path)
            if not m:
                continue
            slug = m.group(1).lower()
            if slug in {"games", "books", "software", "store"}:
                continue
            if clean in seen:
                continue
            seen.add(clean)
            urls.append(clean)
        print(f"[Humble] Bundles encontrados: {len(urls)}")
        return urls

    def get_bundle_title(self) -> str:
        try:
            logo = self.page.locator("img.bundle-logo").first
            if logo.count() > 0:
                alt = (logo.get_attribute("alt") or "").strip()
                if alt:
                    return alt
        except Exception:
            pass
        title = (self.page.title() or "").strip()
        title = re.sub(
            r"\s*\(pay what you want.*$", "", title, flags=re.IGNORECASE
        ).strip()
        return title or "Humble Bundle"

    @staticmethod
    def _parse_money(text: str) -> str:
        """Extrae el primer precio tipo €12.34 / $10 / £8.99."""
        m = re.search(r"([€$£]\s*[\d.,]+|[\d.,]+\s*[€$£])", text or "")
        if not m:
            return ""
        return re.sub(r"\s+", "", m.group(1))

    @staticmethod
    def is_skippable_item(title: str) -> bool:
        return bool(_SKIP_TITLE_RE.search(title or ""))

    def collect_tier_items(self) -> dict:
        """
        Extrae tiers e ítems de la ficha del bundle.
        Devuelve:
          {
            title, tiers: [{price, label, items:[{title, image, msrp}]}],
            items: [{title, image, msrp, tier_price, tier_label}]
          }
        """
        self.page.locator(self.DETAILS_VIEW).first.wait_for(
            state="attached", timeout=20000
        )

        raw = self.page.evaluate(
            """() => {
              const byTitle = {};
              document.querySelectorAll('.tier-item-view').forEach(el => {
                const title = ((el.querySelector('.item-title')||{}).textContent||'').trim();
                const img = el.querySelector('img.item-image');
                const src = img ? (img.getAttribute('src') || img.getAttribute('data-lazy') || '') : '';
                if (title) byTitle[title] = { title, image: src };
              });
              const details = [];
              document.querySelectorAll('.tier-item-details-view').forEach(el => {
                const title = ((el.querySelector('h2')||{}).textContent||'').trim();
                const tier = ((el.querySelector('.tier-price')||{}).textContent||'').replace(/\\s+/g,' ').trim();
                const msrp = ((el.querySelector('.msrp')||{}).textContent||'').replace(/\\s+/g,' ').trim();
                details.push({ title, tier, msrp });
              });
              const headers = [...document.querySelectorAll('h3.tier-header, .js-tier-header')]
                .map(h => (h.textContent||'').replace(/\\s+/g,' ').trim());
              const presets = [...document.querySelectorAll('label.preset-price')]
                .map(l => (l.textContent||'').trim()).filter(Boolean);
              return { byTitle, details, headers, presets };
            }"""
        )

        items = []
        for d in raw.get("details") or []:
            title = (d.get("title") or "").strip()
            if not title:
                continue
            tier_label = (d.get("tier") or "").strip()
            tier_price = self._parse_money(tier_label)
            img = ""
            if title in (raw.get("byTitle") or {}):
                img = raw["byTitle"][title].get("image") or ""
            items.append(
                {
                    "title": title,
                    "image": img,
                    "msrp": (d.get("msrp") or "").strip(),
                    "tier_price": tier_price,
                    "tier_label": tier_label or (f"Pay at least {tier_price}" if tier_price else ""),
                    "skip": self.is_skippable_item(title),
                }
            )

        # Agrupar por precio de desbloqueo (orden por precio numérico aprox.)
        groups: dict[str, list] = {}
        for it in items:
            key = it["tier_price"] or "unknown"
            groups.setdefault(key, []).append(it)

        def _price_sort_key(p: str) -> float:
            digits = re.sub(r"[^\d.,]", "", p).replace(",", ".")
            try:
                return float(digits)
            except Exception:
                return 9999.0

        tiers = []
        for price in sorted(groups.keys(), key=_price_sort_key):
            group_items = groups[price]
            label = group_items[0].get("tier_label") or f"Pay at least {price}"
            # Preferir cabecera de página si coincide el precio
            for h in raw.get("headers") or []:
                if price and price in h.replace(" ", ""):
                    label = h
                    break
            tiers.append(
                {
                    "price": price,
                    "label": label,
                    "items": group_items,
                    "game_count": sum(1 for x in group_items if not x.get("skip")),
                }
            )

        result = {
            "title": self.get_bundle_title(),
            "tiers": tiers,
            "items": items,
            "presets": raw.get("presets") or [],
            "headers": raw.get("headers") or [],
        }
        print(
            f"[Humble] '{result['title']}': {len(items)} items, "
            f"{len(tiers)} tiers"
        )
        return result
