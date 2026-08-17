from urllib.parse import quote_plus, unquote
import re
from difflib import SequenceMatcher

from playwright.sync_api import Page
from pages.base_page import BasePage
from enum import Enum


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
    CATEGORY_ELEMENT = "#category_block a, .game_area_details_specs a"
    # Precio: se resuelve en get_price() sobre el bloque de compra del juego base
    PRICE_IN_BLOCK = ".discount_final_price, .game_purchase_price.price, .game_purchase_price"
    GAME_LABEL = "#app_tagging_modal a.app_tag, #app_tagging_modal div div:nth-child(2) div div a"
    APP_TAGS = "div.glance_tags.popular_tags a.app_tag, a.app_tag"
    GAME_NAME = "#appHubAppName"
    HEADER_IMAGE = (
        "img.game_header_image_full, "
        ".game_header_image_ctn img, "
        "#gameHeaderImageCtn img"
    )
    GAME_RELEASE_DATE = "div.release_date div.date"
    GAME_DEVELOPER_NAME = "#developers_list a, #developers_list"
    GAME_EDITOR_NAME = "#genresAndManufacturer .dev_row:has(b:has-text('Publisher')) .summary a, div.dev_row:has(#developers_list) + div.dev_row .summary a, div.dev_row div.summary.column:not(#developers_list) a"
    REVIEW_SUMMARY = "#userReviews .game_review_summary, .user_reviews_summary_row .game_review_summary"
    REJECT_COOKIES_BUTTON = "#rejectAllButton"
    NOT_AUTHORISED_BUTTON = "#notAuthorisedButton"
    AGE_YEAR_SELECT = "#ageYear"
    AGE_SUBMIT_BUTTON = "#view_product_page_btn"
    TAG_BUTTON = "#glanceCtnResponsiveRight .app_tag.add_button, #add_button_responsive, #glanceCtnResponsiveRight div:nth-child(2) div:nth-child(2) div"
    HIDE_LIVE_BROADCAST_BUTTON = ".broadcast_hover_ctn .broadcast_hover_ctn_hide, #game_highlights .broadcast_embed_top_ctn button, #game_highlights div:nth-child(1) div div:nth-child(1) div:nth-child(1) div:nth-child(3)"
    SEARCH_BAR = "#store_nav_search_term, input[name='term'], input[placeholder*='search' i]"
    FIRST_RESULT = "#search_resultsRows a[data-ds-appid], #search_resultsRows a:first-child"
    SEARCH_RESULT_ROWS = "#search_resultsRows a[data-ds-appid], #search_resultsRows a[href*='/app/']"
    PURCHASE_BLOCKS = "#game_area_purchase .game_area_purchase_game, .game_area_purchase_game"
    FILTERED_WARNING = ".search_results_filtered_warning, #search_results_filtered_warning"
    FILTERED_EXCLUDED_LINK = (
        ".search_results_filtered_warning a[href*='/app/'], "
        ".search_results_filtered_warning a[href*='/sub/'], "
        ".search_results_filtered_warning a[href*='/bundle/']"
    )
    FILTERED_SETTINGS_TAB = ".search_results_filtered_warning .settings_tab, .settings_tab"
    UNFILTERED_RESULTS_BTN = (
        ".newmodal .btn_green_steamui:has-text('sin filtrar'), "
        ".newmodal .btn_green_steamui:has-text('unfiltered'), "
        ".newmodal_buttons .btn_green_steamui"
    )

    def __init__(self, page: Page):
        super().__init__(page)

    def _goto(self, url: str, timeout: float = 30000):
        self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    def _is_steam_game_page(self) -> bool:
        """True si la página actual parece una ficha de juego/app de Steam."""
        url = (self.page.url or "").lower()
        if "/app/" in url or "/sub/" in url or "/bundle/" in url:
            try:
                self.page.locator(self.GAME_NAME).first.wait_for(state="attached", timeout=4000)
                return True
            except Exception:
                return "/app/" in url
        return False

    @staticmethod
    def _normalize_title(text: str | None) -> str:
        """Normaliza títulos para comparar (minúsculas, sin símbolos raros)."""
        if not text:
            return ""
        # Solo primera línea (los resultados Steam meten fecha/precio debajo)
        t = str(text).split("\n", 1)[0]
        t = t.casefold().replace("™", "").replace("®", "").replace("©", "")
        t = unquote(t)
        # "Nightshade/百花百狼" -> quedarnos con partes separadas luego
        t = t.replace("_", " ").replace("-", " ").replace(":", " ").replace("/", " ")
        t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    # Sufijos/ediciones que no identifican el juego por sí solos
    _EDITION_STOPWORDS = frozenset({
        "edition", "standard", "deluxe", "definitive", "complete", "goty",
        "game", "of", "the", "year", "ultimate", "gold", "premium", "digital",
        "remastered", "remaster", "collection", "bundle",
        "season", "pass", "demo", "trial",
        "vr", "supported", "includes", "games", "and", "a", "an",
        "la", "el", "los", "las", "de", "del", "un", "una", "enhanced",
        "super", "mega", "hd", "redux", "legacy", "anniversary", "world",
        "tour", "full", "clip", "directors", "director", "cut",
    })

    _NON_BASE_RE = re.compile(
        r"\b("
        r"soundtrack|\bost\b|deluxe\s+content|season\s+pass|cosmetic|"
        r"skin\s*pack|wallpaper|artbook|art\s*book|bonus\s+content|"
        r"original\s+soundtrack|music|theme|avatar|"
        r"dlc(?:\s+pack)?|content\s+pack|"
        r"\d+\s*%\s*off|coupon"
        r")\b",
        re.IGNORECASE,
    )

    @classmethod
    def _core_tokens(cls, text: str | None) -> list[str]:
        norm = cls._normalize_title(text)
        return [
            t for t in norm.split()
            if t and t not in cls._EDITION_STOPWORDS and not t.isdigit()
        ]

    @classmethod
    def _is_non_base_product(cls, title: str | None) -> bool:
        return bool(cls._NON_BASE_RE.search(title or ""))

    @classmethod
    def _search_query_variants(cls, game_name: str) -> list[str]:
        """Variantes de búsqueda: original, sin edición, parte antes de '/'."""
        variants = []
        raw = (game_name or "").strip()
        if not raw:
            return variants
        variants.append(raw)
        # Parte EN antes de slash bilingüe
        if "/" in raw:
            left = raw.split("/", 1)[0].strip()
            if left and left not in variants:
                variants.append(left)
        # Quitar sufijos de edición comunes
        stripped = re.sub(
            r"[\s:\-–—]*(standard|deluxe|definitive|complete|goty|"
            r"game of the year|gold|ultimate|premium|digital|"
            r"remastered|remaster)?\s*edition\s*$",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip(" -:\u2013\u2014")
        if stripped and stripped.casefold() != raw.casefold() and stripped not in variants:
            variants.append(stripped)
        # Solo tokens core unidos (útil ES/EN ruidoso)
        core = " ".join(cls._core_tokens(raw))
        if core and core not in variants and len(core) >= 3:
            variants.append(core)
        # Dedup preservando orden
        seen = set()
        out = []
        for v in variants:
            key = v.casefold()
            if key not in seen:
                seen.add(key)
                out.append(v)
        return out

    @classmethod
    def _title_match_score(cls, target: str, candidate: str) -> float:
        """
        Score 0..1. Exige solape de tokens del nombre (no solo 'Deluxe Edition').
        Penaliza DLC/soundtrack si el objetivo es el juego base.
        """
        cand_line = (candidate or "").split("\n", 1)[0].strip()
        a = cls._normalize_title(target)
        b = cls._normalize_title(cand_line)
        if not a or not b:
            return 0.0

        target_is_extra = cls._is_non_base_product(target)
        cand_is_extra = cls._is_non_base_product(cand_line)

        # Soundtrack/DLC cuando buscamos el juego base (o al revés)
        penalty = 0.0
        if cand_is_extra and not target_is_extra:
            penalty = 0.50
        elif target_is_extra and not cand_is_extra:
            penalty = 0.40

        if a == b:
            return max(0.0, 1.0 - penalty)

        core_a = cls._core_tokens(target)
        core_b = cls._core_tokens(cand_line)

        # Sin tokens distintivos (solo "Deluxe Edition"): casi nulo
        if not core_a:
            seq = SequenceMatcher(None, a, b).ratio()
            return max(0.0, seq * 0.4 - penalty)

        if not core_b:
            return 0.0

        set_a, set_b = set(core_a), set(core_b)
        overlap = len(set_a & set_b)
        # El candidato debe cubrir buena parte del nombre buscado
        recall = overlap / len(set_a)
        precision = overlap / len(set_b)

        if recall < 0.5:
            # Menos de la mitad de las palabras clave: no es el juego
            # (evita Borderlands 3 <-> RENNSPORT Standard Edition)
            seq = SequenceMatcher(None, a, b).ratio()
            return max(0.0, min(seq, 0.45) * recall - penalty)

        containment = 0.0
        if a in b or b in a:
            shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
            containment = 0.15 * (len(shorter) / max(len(longer), 1))

        seq = SequenceMatcher(None, a, b).ratio()
        score = (
            0.55 * recall
            + 0.25 * precision
            + 0.15 * seq
            + containment
        )
        if set_a == set_b:
            score = max(score, 0.92)
        elif set_a.issubset(set_b) or set_b.issubset(set_a):
            score = max(score, 0.8 + 0.1 * min(recall, precision))

        return max(0.0, min(1.0, score - penalty))

    def _title_from_href(self, href: str | None) -> str:
        """Intenta sacar un nombre legible del slug de /app/id/Name_Here/."""
        if not href:
            return ""
        m = re.search(r"/app/\d+/([^/?#]+)", href)
        if not m:
            return ""
        return unquote(m.group(1).replace("_", " ").replace("+", " ")).strip()

    def _result_title(self, link) -> str:
        """Título limpio de un resultado de búsqueda (sin fecha/precio)."""
        try:
            title_el = link.locator(".title, .search_name .title").first
            if title_el.count() > 0:
                t = (title_el.inner_text(timeout=500) or "").strip()
                if t:
                    return t.split("\n", 1)[0].strip()
        except Exception:
            pass
        try:
            text = (link.inner_text(timeout=800) or "").strip()
            return text.split("\n", 1)[0].strip() if text else ""
        except Exception:
            return ""

    def _rank_link_matches(
        self,
        links,
        game_name: str | None,
        limit: int = 8,
    ) -> list[tuple[int, float, str, str]]:
        """Lista [(index, score, title, href)] ordenada por score desc."""
        count = links.count()
        if count == 0 or not game_name:
            return []
        ranked = []
        for i in range(count):
            link = links.nth(i)
            text = self._result_title(link)
            href = ""
            try:
                href = link.get_attribute("href") or ""
            except Exception:
                pass
            from_href = self._title_from_href(href)
            score = max(
                self._title_match_score(game_name, text),
                self._title_match_score(game_name, from_href),
            )
            label = text or from_href or href
            ranked.append((i, score, label, href))
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:limit]

    def _pick_best_link_index(
        self,
        links,
        game_name: str | None,
        min_score: float = 0.72,
    ) -> int | None:
        """
        Elige el índice del enlace cuyo texto/href mejor coincide con game_name.
        Si no hay game_name o nadie supera min_score, None (NO caer al primero).
        """
        if not game_name:
            return 0 if links.count() else None
        ranked = self._rank_link_matches(links, game_name, limit=5)
        if not ranked:
            return None
        best_i, best_score, best_label, _ = ranked[0]
        if best_score < min_score:
            print(
                f"[Steam] Sin match de nombre suficiente para '{game_name}' "
                f"(mejor={best_score:.2f}: {best_label!r})"
            )
            return None
        print(
            f"[Steam] Match por nombre '{game_name}' -> "
            f"#{best_i} {best_label!r} (score={best_score:.2f})"
        )
        return best_i

    def _click_first_search_result(
        self,
        timeout: float = 5000,
        game_name: str | None = None,
        min_score: float = 0.72,
    ) -> bool:
        """Abre el mejor resultado; si no hay match fiable, no hace click a ciegas."""
        rows = self.page.locator(self.SEARCH_RESULT_ROWS)
        try:
            rows.first.wait_for(state="visible", timeout=timeout)
        except Exception:
            first_result = self.page.locator(self.FIRST_RESULT).first
            try:
                first_result.wait_for(state="visible", timeout=timeout)
            except Exception:
                return False
            if not game_name:
                first_result.click()
                self.page.wait_for_load_state("domcontentloaded")
                return True
            # Un solo resultado visible: solo si el nombre encaja
            idx = self._pick_best_link_index(
                self.page.locator(self.FIRST_RESULT), game_name, min_score=min_score
            )
            if idx is None:
                return False
            self.page.locator(self.FIRST_RESULT).nth(idx).click()
            self.page.wait_for_load_state("domcontentloaded")
            return True

        idx = self._pick_best_link_index(rows, game_name, min_score=min_score)
        if idx is None:
            return False
        try:
            rows.nth(idx).click()
            self.page.wait_for_load_state("domcontentloaded")
            return True
        except Exception:
            return False

    def _try_open_ranked_candidates(
        self,
        game_name: str,
        min_score: float = 0.72,
        max_tries: int = 4,
    ) -> bool:
        """Prueba los mejores candidatos y verifica el título en la ficha."""
        rows = self.page.locator(self.SEARCH_RESULT_ROWS)
        try:
            rows.first.wait_for(state="visible", timeout=6000)
        except Exception:
            return False

        ranked = self._rank_link_matches(rows, game_name, limit=max_tries)
        search_url = self.page.url
        for idx, score, label, href in ranked:
            if score < min_score:
                break
            print(
                f"[Steam] Probando candidato #{idx} {label!r} (score={score:.2f})"
            )
            try:
                # Preferir navegación directa por href (más estable)
                if href and "/app/" in href:
                    abs_url = href if href.startswith("http") else "https://store.steampowered.com" + href
                    self.page.goto(abs_url, wait_until="domcontentloaded", timeout=30000)
                else:
                    rows.nth(idx).click()
                    self.page.wait_for_load_state("domcontentloaded")
                self.handle_initial_overlays()
                if not self._is_steam_game_page():
                    self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    continue
                opened_name = self.get_game_name()
                verify = self._title_match_score(game_name, opened_name)
                print(
                    f"[Steam] Verificacion '{game_name}' vs '{opened_name}' "
                    f"-> {verify:.2f}"
                )
                if verify >= 0.65:
                    return True
                print("[Steam] Candidato descartado tras verificar ficha")
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                rows = self.page.locator(self.SEARCH_RESULT_ROWS)
                rows.first.wait_for(state="visible", timeout=6000)
            except Exception as e:
                print(f"[Steam] Error con candidato #{idx}: {e}")
                try:
                    self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    pass
        return False

    def _reveal_preference_filtered_results(self, game_name: str | None = None) -> bool:
        """
        Si Steam ocultó resultados por preferencias, muestra los excluidos.
        1) Entre los enlaces excluidos, el que mejor coincida (sin fallback al 1º)
        2) Engranaje -> resultados sin filtrar + match
        3) Recarga con ignore_preferences=1 + match
        """
        excluded = self.page.locator(self.FILTERED_EXCLUDED_LINK)
        try:
            if excluded.count() > 0 and excluded.first.is_visible(timeout=1500):
                n = excluded.count()
                print(f"[Steam] {n} titulo(s) excluido(s) por preferencias")
                ranked = self._rank_link_matches(excluded, game_name, limit=5)
                for idx, score, label, href in ranked:
                    if score < 0.72:
                        break
                    print(
                        f"[Steam] Abriendo excluido #{idx} {label!r} "
                        f"(score={score:.2f}) -> {href}"
                    )
                    if href and "/app/" in href:
                        abs_url = (
                            href if href.startswith("http")
                            else "https://store.steampowered.com" + href
                        )
                        self.page.goto(abs_url, wait_until="domcontentloaded", timeout=30000)
                    else:
                        excluded.nth(idx).click()
                        self.page.wait_for_load_state("domcontentloaded")
                    self.handle_initial_overlays()
                    if self._is_steam_game_page():
                        opened = self.get_game_name()
                        if not game_name or self._title_match_score(game_name, opened) >= 0.65:
                            return True
                    # seguir con el siguiente excluido
                print("[Steam] Ningun excluido encajo bien; probando sin filtrar")
        except Exception as e:
            print(f"[Steam] Error eligiendo titulo excluido: {e}")

        try:
            warning = self.page.locator(self.FILTERED_WARNING).first
            if warning.count() > 0 and warning.is_visible(timeout=1000):
                tab = self.page.locator(self.FILTERED_SETTINGS_TAB).first
                if tab.count() > 0:
                    print("[Steam] Abriendo opciones de resultados excluidos por preferencias")
                    tab.click(force=True, timeout=3000)
                    btn = self.page.locator(self.UNFILTERED_RESULTS_BTN).first
                    btn.wait_for(state="visible", timeout=4000)
                    print("[Steam] Seleccionando 'Ver resultados de busqueda sin filtrar'")
                    btn.click(timeout=3000)
                    self.page.wait_for_load_state("domcontentloaded")
                    self.page.wait_for_timeout(800)
                    if game_name:
                        return self._try_open_ranked_candidates(game_name)
                    return self._click_first_search_result(timeout=8000, game_name=game_name)
        except Exception as e:
            print(f"[Steam] No se pudo usar el modal de preferencias: {e}")

        try:
            current = self.page.url
            if "ignore_preferences=1" not in current:
                sep = "&" if "?" in current else "?"
                unfiltered = f"{current}{sep}ignore_preferences=1"
                print(f"[Steam] Recargando busqueda sin preferencias: {unfiltered}")
                self.page.goto(unfiltered, wait_until="domcontentloaded", timeout=30000)
                if game_name:
                    return self._try_open_ranked_candidates(game_name)
                return self._click_first_search_result(timeout=8000, game_name=game_name)
        except Exception as e:
            print(f"[Steam] Fallback ignore_preferences fallo: {e}")

        return False

    def open_game_by_name_and_extract_data(
        self,
        game_name: str,
        include_image: bool = False,
    ) -> dict | None:
        print(f"[Steam] Buscando: '{game_name}'")

        steam_page = self.page.context.new_page()
        steam_game = SteamGamePage(steam_page)

        try:
            opened = False
            for variant in self._search_query_variants(game_name):
                # category1=998 -> solo juegos (reduce software/DLC ruidoso)
                search_url = (
                    "https://store.steampowered.com/search/"
                    f"?term={quote_plus(variant)}&category1=998&ignore_preferences=1"
                )
                print(f"[Steam] Query: '{variant}'")
                steam_page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                steam_game.handle_initial_overlays()

                opened = steam_game._try_open_ranked_candidates(game_name, min_score=0.72)
                if not opened:
                    opened = steam_game._reveal_preference_filtered_results(game_name)
                if opened:
                    break

            if not opened:
                print(f"[Steam] No hay resultados fiables para '{game_name}'")
                return None

            steam_game.handle_initial_overlays()
            if not steam_game._is_steam_game_page():
                print(f"[Steam] La busqueda de '{game_name}' no abrio una ficha de juego")
                return None

            data = steam_game.extract_all_data(include_image=include_image)
            verify = self._title_match_score(game_name, data.get("game_name") or "")
            if verify < 0.65:
                print(
                    f"[Steam] Descartado resultado final '{data.get('game_name')}' "
                    f"para '{game_name}' (score={verify:.2f})"
                )
                return None
            print(f"[Steam] Extraido: {data['game_name']}")
            return data

        except Exception as e:
            print(f"[Steam] Error con '{game_name}': {e}")
            return None

        finally:
            steam_page.close()

    def open_url_and_extract_data(
        self,
        url: str,
        game_name: str | None = None,
        include_image: bool = False,
    ) -> dict | None:
        """
        Abre una URL de Steam y extrae datos.
        Si la URL lleva al home/store (o no es ficha de juego), busca por game_name.
        """
        steam_page = self.page.context.new_page()
        try:
            steam_page.goto(url, wait_until="domcontentloaded", timeout=30000)
            steam_game = SteamGamePage(steam_page)
            steam_game.handle_initial_overlays()

            if steam_game._is_steam_game_page():
                return steam_game.extract_all_data(include_image=include_image)

            # Fallback: enlace inválido / home de Steam
            if game_name:
                print(
                    f"[Steam] URL no es ficha de juego ({steam_page.url}). "
                    f"Buscando por nombre: '{game_name}'"
                )
                steam_page.close()
                steam_page = None
                return self.open_game_by_name_and_extract_data(
                    game_name, include_image=include_image
                )

            print(f"[Steam] URL no es ficha de juego y no hay nombre para buscar: {steam_page.url}")
            return None
        except Exception as e:
            print(f"[Steam] Error abriendo '{url}': {e}")
            if game_name:
                print(f"[Steam] Fallback: buscando '{game_name}'")
                try:
                    if steam_page:
                        steam_page.close()
                        steam_page = None
                except Exception:
                    pass
                return self.open_game_by_name_and_extract_data(
                    game_name, include_image=include_image
                )
            return None
        finally:
            if steam_page:
                try:
                    steam_page.close()
                except Exception:
                    pass

    def extract_all_data(self, include_image: bool = False) -> dict:
        data = {
            "game_name": self.get_generic_data(SteamGamePageData.GAME_NAME),
            "url": self.get_generic_data(SteamGamePageData.URL),
            "price": self.get_generic_data(SteamGamePageData.PRICE),
            "reviews": self.get_generic_data(SteamGamePageData.REVIEWS),
            "categories": self.get_generic_data(SteamGamePageData.CATEGORIES),
            "game_label": self.get_generic_data(SteamGamePageData.GAME_LABEL),
            "release_date": self.get_generic_data(SteamGamePageData.RELEASE_DATE),
            "editor": self.get_generic_data(SteamGamePageData.EDITOR),
            "developer": self.get_generic_data(SteamGamePageData.DEVELOPER),
        }
        if include_image:
            images = self.get_header_image_candidates()
            data["header_image"] = images[0] if images else ""
            data["header_image_fallbacks"] = images[1:] if len(images) > 1 else []
        return data

    def get_header_image_candidates(self) -> list[str]:
        """Portadas Steam: DOM real primero, luego CDN header/capsule (varios hosts)."""
        urls: list[str] = []

        try:
            img = self.page.locator(self.HEADER_IMAGE)
            if img.count() > 0:
                src = (img.first.get_attribute("src") or "").strip()
                if src.startswith("//"):
                    src = "https:" + src
                if src:
                    urls.append(src)
        except Exception:
            pass

        appid = None
        m = re.search(r"/app/(\d+)", self.page.url or "")
        if m:
            appid = m.group(1)
        if not appid:
            for u in urls:
                m2 = re.search(r"/apps/(\d+)/", u)
                if m2:
                    appid = m2.group(1)
                    break

        if appid:
            hosts = (
                "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps",
                "https://cdn.cloudflare.steamstatic.com/steam/apps",
                "https://cdn.akamai.steamstatic.com/steam/apps",
            )
            assets = ("header.jpg", "capsule_616x353.jpg", "capsule_231x87.jpg")
            for host in hosts:
                for asset in assets:
                    urls.append(f"{host}/{appid}/{asset}")

        seen: set[str] = set()
        unique: list[str] = []
        for u in urls:
            # Normalizar sin query para dedupe, pero conservar ?t= del DOM como primera opción
            key = u.split("?")[0]
            if key in seen:
                continue
            seen.add(key)
            unique.append(u)
        return unique

    def get_header_image(self) -> str:
        """URL de portada Steam (primera candidata)."""
        candidates = self.get_header_image_candidates()
        return candidates[0] if candidates else ""

    def searchGameOnSteamByName(self, game_name: str):
        print(f"[Steam] Buscando: {game_name}")
        steam_page = self.page.context.new_page()
        search_url = f"https://store.steampowered.com/search/?term={quote_plus(game_name)}"
        try:
            steam_page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            first_result = steam_page.locator(self.FIRST_RESULT).first
            first_result.wait_for(state="visible", timeout=8000)
            first_result.click()
            steam_page.wait_for_load_state("domcontentloaded")
            name = steam_page.locator(self.GAME_NAME).inner_text().strip()
            print(f"[Steam] Nombre encontrado: {name}")
        except Exception as e:
            print(f"[Steam] Error buscando '{game_name}': {e}")
        finally:
            steam_page.close()

    def get_game_name(self) -> str:
        name = self._safe_text(self.GAME_NAME)
        print(f"[Steam] GameName: {name}")
        return name

    def _purchase_block_title(self, block) -> str:
        for sel in ("h1", "h2"):
            title = block.locator(sel)
            if title.count() > 0:
                return title.first.inner_text().strip()
        return ""

    def _is_base_game_purchase_block(self, title: str) -> bool:
        lower = title.lower()
        if not title:
            return False
        skip_tokens = (
            " demo",
            "demo ",
            "soundtrack",
            " bundle",
            "bundle ",
            " dlc",
            "dlc ",
            "season pass",
        )
        # "Download X Demo" / títulos que empiezan por Download
        if lower.startswith("download "):
            return False
        if any(token in lower for token in skip_tokens):
            return False
        return lower.startswith("buy ")

    def _price_from_block(self, block) -> str | None:
        # Descuento: evitar "Your Price:" de bundles con ownership
        discounted = block.locator(".discount_final_price")
        for i in range(discounted.count()):
            text = discounted.nth(i).inner_text().strip()
            cleaned = " ".join(text.split())
            if cleaned and "your price" not in cleaned.lower():
                # Si hay varias líneas (label + precio), quedarse con la que parece precio
                for part in cleaned.replace("|", "\n").split("\n"):
                    part = part.strip()
                    if part and "your price" not in part.lower() and any(ch.isdigit() for ch in part):
                        return part
                if any(ch.isdigit() for ch in cleaned):
                    return cleaned

        regular = block.locator(".game_purchase_price.price, .game_purchase_price")
        if regular.count() > 0:
            text = regular.first.inner_text().strip()
            if text:
                return " ".join(text.split())

        # Free to Play / Free
        free = block.locator(".game_purchase_price, .game_area_purchase_game_dropdown_selection")
        if free.count() > 0:
            text = free.first.inner_text().strip()
            if text and "free" in text.lower():
                return text
        return None

    def get_price(self) -> str:
        blocks = self.page.locator(self.PURCHASE_BLOCKS)
        blocks.first.wait_for(state="attached", timeout=8000)

        # 1) Bloque "Buy <game>" (ignora Demo / Bundle / DLC)
        for i in range(blocks.count()):
            block = blocks.nth(i)
            title = self._purchase_block_title(block)
            if self._is_base_game_purchase_block(title):
                price = self._price_from_block(block)
                if price:
                    return price

        # 2) Fallback: primer bloque con precio usable (no demo)
        for i in range(blocks.count()):
            block = blocks.nth(i)
            title = self._purchase_block_title(block).lower()
            if "demo" in title or "download" in title:
                continue
            price = self._price_from_block(block)
            if price:
                return price

        # 3) Último recurso: cualquier data-price-final / precio visible
        for sel in (
            "#game_area_purchase .discount_final_price",
            "#game_area_purchase .game_purchase_price",
            "[data-price-final]",
        ):
            loc = self.page.locator(sel)
            for i in range(min(loc.count(), 5)):
                text = loc.nth(i).inner_text().strip()
                cleaned = " ".join(text.split())
                if cleaned and "your price" not in cleaned.lower() and any(ch.isdigit() for ch in cleaned):
                    # data-price-final suele traer "-20% 12,25€ 9,80€" → quedarse con el último token con dígitos
                    parts = [p for p in cleaned.replace("|", " ").split() if any(ch.isdigit() for ch in p)]
                    return parts[-1] if parts else cleaned

        raise RuntimeError("No se encontro precio en la pagina de Steam")

    def _parse_review_tooltip(self, tooltip: str | None, fallback_text: str = "") -> str:
        """
        Convierte tooltips Steam en 'XX% (N)' o fallback legible.
        Ej: '82% of the 1,211 user reviews...' -> '82% (1,211)'
            'Need more user reviews...' + '5 user reviews' -> '5 reseñas'
        """
        text = (tooltip or "").strip()
        fb = " ".join((fallback_text or "").split())

        # Porcentaje + número de reviews
        m = re.search(
            r"(\d+)\s*%\s*(?:of the|de las|de los)?\s*([\d.,\s]+)\s*(?:user reviews|reseñas)",
            text,
            flags=re.IGNORECASE,
        )
        if m:
            pct = m.group(1)
            count = m.group(2).strip().replace(" ", "")
            return f"{pct}% ({count})"

        # Solo porcentaje (por si cambia el formato)
        m_pct = re.search(r"(\d+)\s*%", text)
        m_count = re.search(r"([\d.,]+)\s*(?:user reviews|reseñas)", text, flags=re.IGNORECASE)
        if m_pct and m_count:
            return f"{m_pct.group(1)}% ({m_count.group(1).replace(' ', '')})"

        # Sin score: '5 user reviews' / '4 reseña(s) de usuario(s)'
        for source in (fb, text):
            m_only = re.search(
                r"([\d.,]+)\s*(?:user reviews|reseñas?(?:\(s\))?|reseña\(s\) de usuario\(s\))",
                source,
                flags=re.IGNORECASE,
            )
            if m_only:
                return f"{m_only.group(1).replace(' ', '')} reseñas"

            m_paren = re.search(r"\(([\d.,]+)\)", source)
            if m_paren and ("review" in source.lower() or "reseña" in source.lower()):
                return f"{m_paren.group(1)} reseñas"

        if not text and not fb:
            return "N/A"
        if "need more" in text.lower() or "n/a" in fb.lower() or "no user reviews" in text.lower():
            # Si hay número en el texto visible, usarlo
            m_fb = re.search(r"([\d.,]+)\s*(?:user reviews|reseñas)", fb, flags=re.IGNORECASE)
            if m_fb:
                return f"{m_fb.group(1).replace(' ', '')} reseñas"
            return "N/A"
        short = fb or text
        if len(short) <= 40:
            return short
        return "N/A"

    def get_reviews(self) -> str:
        """
        Formato con Global primero (más importante):
          Global: 82% (1,211)
          30 días: 76% (13)
        """
        recent = "N/A"
        overall = "N/A"
        try:
            container = self.page.locator("#userReviews")
            if container.count() == 0:
                return "30 días: N/A\nGlobal: N/A"
            container.first.wait_for(state="attached", timeout=4000)

            rows = container.locator("a.user_reviews_summary_row")
            for i in range(rows.count()):
                row = rows.nth(i)
                tooltip = row.get_attribute("data-tooltip-html") or ""
                label = ""
                try:
                    subtitle = row.locator(".subtitle").first
                    if subtitle.count():
                        label = subtitle.inner_text().strip().lower()
                except Exception:
                    pass
                row_text = ""
                try:
                    row_text = row.inner_text()
                except Exception:
                    pass

                parsed = self._parse_review_tooltip(tooltip, row_text)
                tip_l = tooltip.lower()
                is_recent = (
                    "30" in tip_l
                    or "last 30" in tip_l
                    or "últimos 30" in tip_l
                    or "ultimos 30" in tip_l
                    or "recent" in label
                    or "recientes" in label
                )
                is_overall = (
                    "all reviews" in label
                    or "todas" in label
                    or "for this game" in tip_l
                    or "sobre este juego" in tip_l
                )

                if is_recent:
                    recent = parsed
                elif is_overall:
                    overall = parsed
                elif overall == "N/A":
                    overall = parsed

        except Exception as e:
            print(f"[Steam] Error en get_reviews: {e}")

        result = f"Global: {overall}\n30 días: {recent}"
        print(f"[Steam] Review: {result.replace(chr(10), ' | ')}")
        return result

    def get_categories(self) -> str:
        elements = self.page.locator(self.CATEGORY_ELEMENT)
        texts = []
        for i in range(elements.count()):
            text = elements.nth(i).inner_text().strip()
            if text and text != "?":
                texts.append(text)
        return ", ".join(texts)

    def get_game_label(self) -> list[str] | None:
        # Rápido: tags ya visibles en la ficha (sin abrir modal)
        try:
            visible_tags = self.page.locator(self.APP_TAGS)
            if visible_tags.count() > 0:
                tags = []
                for i in range(visible_tags.count()):
                    text = visible_tags.nth(i).inner_text().strip()
                    if text and text.lower() not in {"+", "add a tag"}:
                        tags.append(text)
                if tags:
                    return tags
        except Exception:
            pass

        # Fallback: abrir modal de tags
        try:
            tag_button = self.page.locator(self.TAG_BUTTON).first
            if tag_button.is_visible(timeout=1500):
                print("[Steam] Clicking GAME TAG BUTTON")
                tag_button.click(timeout=3000)
                self.page.wait_for_timeout(300)
                elements = self.page.locator(self.GAME_LABEL)
                tags = []
                for i in range(elements.count()):
                    text = elements.nth(i).inner_text().strip()
                    if text:
                        tags.append(text)
                return tags or None
        except Exception as e:
            print("[Steam] Error en get_game_label()")
            print(e)
        return None

    def get_release_date(self) -> str:
        return self._safe_text(self.GAME_RELEASE_DATE)

    def get_editor(self) -> str:
        return self._safe_text(self.GAME_EDITOR_NAME)

    def get_developer(self) -> str:
        return self._safe_text(self.GAME_DEVELOPER_NAME)

    def get_url(self) -> str:
        return self.page.url

    def _safe_text(self, selector: str) -> str:
        loc = self.page.locator(selector)
        if loc.count() == 0:
            return ""
        return loc.first.inner_text().strip()

    def click_reject_cookies_steam(self):
        try:
            button = self.page.locator(self.REJECT_COOKIES_BUTTON)
            if button.is_visible(timeout=1200):
                print("[Steam] Clicking RejectCookiesButton")
                button.click(timeout=2000)
        except Exception:
            pass

    def click_not_authorised_button(self):
        try:
            button = self.page.locator(self.NOT_AUTHORISED_BUTTON)
            if button.is_visible(timeout=1000):
                print("[Steam] Clicking NotAuthorisedButton")
                button.click(timeout=2000)
                self.page.reload(wait_until="domcontentloaded")
        except Exception:
            pass

    def click_hide_live_stream(self, timeout: float = 1.5):
        try:
            button = self.page.locator(self.HIDE_LIVE_BROADCAST_BUTTON).first
            if button.is_visible(timeout=timeout * 1000):
                print("[Steam] Hiding Live Broadcast")
                button.click(timeout=2000)
        except Exception:
            print("[Steam] Live Broadcast no presente")

    def accept_age_child_control(self):
        try:
            year_select = self.page.locator(self.AGE_YEAR_SELECT)
            if year_select.is_visible(timeout=1500):
                print("[Steam] Manejando control de edad")
                year_select.select_option("1970")
                self.page.locator(self.AGE_SUBMIT_BUTTON).click(timeout=3000)
                self.page.wait_for_load_state("domcontentloaded")
        except Exception:
            pass

    def handle_initial_overlays(self):
        print("[Steam] Limpiando overlays...")
        self.accept_age_child_control()
        self.click_reject_cookies_steam()
        self.click_hide_live_stream()
        self.click_not_authorised_button()
        # Asegurar que el nombre (ficha lista) está presente
        try:
            self.page.locator(self.GAME_NAME).first.wait_for(state="visible", timeout=8000)
        except Exception:
            pass
        print("[Steam] Overlays limpiados")

    def get_generic_data(self, selected_data: SteamGamePageData) -> str:
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
            result = mapping[selected_data]()
            if isinstance(result, list):
                return ", ".join(result)
            return str(result) if result is not None else ""
        except Exception:
            return f"Cannot retrieve '{selected_data.name}' info from steam game!"

    def show_all_game_data(self) -> str:
        datastring = ""
        datastring += self.get_game_name() + " | "
        datastring += self.get_price() + " | "
        datastring += self.get_categories() + " | "
        labels = self.get_game_label()
        datastring += ", ".join(labels) if labels else "N/A"
        print(datastring)
        return datastring
