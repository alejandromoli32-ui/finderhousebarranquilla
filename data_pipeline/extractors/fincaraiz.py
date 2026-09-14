"""
data_pipeline/extractors/fincaraiz.py
Extractor for Finca Raíz rental listings in Barranquilla Norte.
Queries Next.js SSR endpoints and extracts structured __NEXT_DATA__ payloads.
Conforms strictly to PROJECT.md schema.
"""

import json
import logging
import os
import re
import ssl
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("FincaRaizExtractor")

DEFAULT_TARGET_BARRIOS = [
    ("miramar", "Miramar", "Noroccidente"),
    ("villa-carolina", "Villa Carolina", "Norte"),
    ("riomar", "Riomar", "Noroccidente"),
    ("villa-santos", "Villa Santos", "Noroccidente"),
    ("villa-country", "Villa Country", "Norte"),
    ("el-golf", "El Golf", "Norte"),
    ("el-prado", "El Prado", "Norte"),
    ("altos-de-riomar", "Altos de Riomar", "Noroccidente"),
    ("ciudad-mallorquin", "Ciudad Mallorquin", "Noroccidente"),
    ("la-campina", "La Campina", "Noroccidente"),
    ("san-vicente", "San Vicente", "Norte"),
    ("granadillo", "Granadillo", "Noroccidente"),
    ("ciudad-jardin", "Ciudad Jardin", "Noroccidente"),
    ("bellavista", "Bellavista", "Norte"),
    ("el-limoncito", "El Limoncito", "Norte"),
    ("paraiso", "Paraiso", "Norte")
]


class FincaRaizExtractor:
    """
    Extractor for Finca Raíz using SSR __NEXT_DATA__ hydration payloads.
    """

    BASE_URL = "https://www.fincaraiz.com.co"
    MAX_PRICE_CEILING = 2500000

    def __init__(
        self,
        cache_path: Optional[str] = None,
        timeout: int = 15,
        max_retries: int = 3,
        request_delay: float = 0.5
    ):
        self.cache_path = cache_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "cache",
            "fincaraiz_cache.json"
        )
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": "https://www.fincaraiz.com.co/",
        }
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def parse_next_data(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Locates and parses the <script id="__NEXT_DATA__"[^>]*> tag in HTML.
        Returns the raw data list from props.pageProps.fetchResult.searchFast.data.
        """
        if not html_content:
            return []

        pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
        match = re.search(pattern, html_content, re.DOTALL)
        if not match:
            # Fallback for alternative id order or tags
            alt_match = re.search(r'__NEXT_DATA__[^>]*>(.*?)</script>', html_content, re.DOTALL)
            if alt_match:
                match = alt_match
            else:
                return []

        try:
            payload = json.loads(match.group(1))
            page_props = payload.get("props", {}).get("pageProps", {})
            fetch_result = page_props.get("fetchResult", {})
            search_fast = fetch_result.get("searchFast", {})
            data = search_fast.get("data", [])
            if isinstance(data, list):
                return data
            # Check alternative keys
            results = search_fast.get("results", {})
            hits = results.get("hits", []) or results.get("data", [])
            if isinstance(hits, list):
                return hits
        except Exception as e:
            logger.warning(f"Error parsing Finca Raiz __NEXT_DATA__: {e}")

        return []

    def _extract_financials(self, item: Dict[str, Any]) -> Tuple[int, int, int]:
        """
        Extracts (canon, admin_fee, total_price) with robust admin fee detection.
        """
        p = item.get("price", {}) or {}
        ce = item.get("commonExpenses", {}) or {}

        try:
            amount = int(float(p.get("amount") or 0))
        except (ValueError, TypeError):
            amount = 0

        try:
            admin_included = int(float(p.get("admin_included") or 0))
        except (ValueError, TypeError):
            admin_included = 0

        ce_amount = 0
        if isinstance(ce, dict):
            try:
                ce_amount = int(float(ce.get("amount") or 0))
            except (ValueError, TypeError):
                ce_amount = 0
        elif isinstance(ce, (int, float, str)):
            digits = re.sub(r'[^\d]', '', str(ce))
            if digits:
                ce_amount = int(digits)

        # Check technicalSheet if commonExpenses is still 0
        if ce_amount == 0 and item.get("technicalSheet"):
            for field in item.get("technicalSheet", []):
                if isinstance(field, dict) and field.get("field") == "commonExpenses":
                    raw_val = field.get("value")
                    digits = re.sub(r'[^\d]', '', str(raw_val or ""))
                    if digits:
                        try:
                            ce_amount = int(digits)
                            break
                        except ValueError:
                            pass

        if admin_included > 0:
            total = admin_included
            if 0 < amount <= total:
                canon = amount
                admin = total - canon
            else:
                canon = total
                admin = ce_amount if ce_amount > 0 and (total - ce_amount) > 0 else 0
                if admin > 0:
                    canon = total - admin
        else:
            canon = amount
            admin = ce_amount
            total = canon + admin

        return canon, admin, total

    def normalize_property(
        self,
        item: Dict[str, Any],
        default_barrio: str = "Barranquilla",
        default_zone: str = "Norte"
    ) -> Optional[Dict[str, Any]]:
        """
        Transforms raw Finca Raíz listing into canonical schema matching PROJECT.md.
        Enforces total_price <= 2.500.000 COP price ceiling strictly.
        """
        if not isinstance(item, dict):
            return None

        raw_id = item.get("id")
        if not raw_id:
            return None
        prop_id = f"FR-{raw_id}"

        canon, admin_fee, total_price = self._extract_financials(item)

        # Strict price ceiling check
        if total_price <= 0 or total_price > self.MAX_PRICE_CEILING:
            return None

        # Property type
        prop_type_id = item.get("property_type_id") or item.get("typeID")
        title_raw = str(item.get("title") or "")
        link_raw = str(item.get("link") or "")
        if prop_type_id == 1 or "casa" in title_raw.lower() or "/casa/" in link_raw.lower():
            property_type = "Casa"
        else:
            property_type = "Apartamento"

        # Neighborhood & Zone
        locations = item.get("locations") or {}
        loc_main = (locations.get("location_main") or {}).get("name")
        neigh_list = locations.get("neighbourhood") or []
        first_neigh = neigh_list[0].get("name") if neigh_list and isinstance(neigh_list[0], dict) else None

        if loc_main and loc_main.lower() != "barranquilla":
            neighborhood = loc_main
        elif first_neigh:
            neighborhood = first_neigh
        else:
            neighborhood = default_barrio

        # Clean noise
        neighborhood = re.sub(r'(?i)\b(noroccidente|norte|barranquilla|atlantico)\b', '', neighborhood).strip()
        if not neighborhood:
            neighborhood = default_barrio

        # Zone
        locality = str(locations.get("locality") or locations.get("zone") or "").lower()
        if "noroccidente" in locality or "riomar" in locality or "miramar" in neighborhood.lower():
            zone = "Noroccidente"
        elif "norte" in locality:
            zone = "Norte"
        else:
            zone = default_zone

        # Technical specs
        tech_dict: Dict[str, Any] = {}
        for f in item.get("technicalSheet", []) or []:
            if isinstance(f, dict) and f.get("field"):
                tech_dict[f["field"]] = f.get("value")

        # Area
        try:
            raw_m2 = item.get("m2") or item.get("m2Built") or tech_dict.get("area") or 0
            m = re.search(r'(\d+(?:\.\d+)?)', str(raw_m2))
            area_m2 = float(m.group(1)) if m else 0.0
        except (ValueError, TypeError):
            area_m2 = 0.0

        # Bedrooms
        try:
            raw_bed = item.get("bedrooms") or item.get("rooms") or tech_dict.get("bedrooms") or 1
            bedrooms = int(float(raw_bed))
        except (ValueError, TypeError):
            bedrooms = 1

        # Bathrooms
        try:
            raw_bath = item.get("bathrooms") or tech_dict.get("bathrooms") or 1
            bathrooms = int(float(raw_bath))
        except (ValueError, TypeError):
            bathrooms = 1

        # Parking
        try:
            raw_park = item.get("garage") or tech_dict.get("garage") or 0
            parking = int(float(raw_park))
        except (ValueError, TypeError):
            parking = 0

        # Stratum
        try:
            raw_stratum = item.get("stratum") or tech_dict.get("stratum") or 4
            stratum = int(float(raw_stratum))
        except (ValueError, TypeError):
            stratum = 4

        # Title & URL
        title = title_raw or f"{property_type} en Arriendo en {neighborhood}, Barranquilla"
        if link_raw.startswith("/"):
            url = f"{self.BASE_URL}{link_raw}"
        elif link_raw.startswith("http"):
            url = link_raw
        else:
            url = f"{self.BASE_URL}/inmueble/{raw_id}"

        # Images
        images: List[str] = []
        cover_img = item.get("img")
        if cover_img and isinstance(cover_img, str) and cover_img.startswith("http"):
            images.append(cover_img)

        raw_images = item.get("images") or []
        for img_obj in raw_images:
            if isinstance(img_obj, dict):
                img_url = img_obj.get("image") or img_obj.get("url")
            elif isinstance(img_obj, str):
                img_url = img_obj
            else:
                img_url = None

            if img_url and isinstance(img_url, str) and img_url.startswith("http") and img_url not in images:
                images.append(img_url)

        # Description
        description = str(item.get("description") or "").strip()

        # Contact
        owner = item.get("owner") or {}
        agency = str(owner.get("name") or "Inmobiliaria Finca Raíz").strip()
        masked_phone = str(owner.get("masked_phone") or "").strip()

        # Attempt to find unmasked phone from description
        phone = ""
        desc_phones = re.findall(r'\b(3\d{2}[-.\s]?\d{3}[-.\s]?\d{4})\b', description)
        if desc_phones:
            phone = re.sub(r'\D', '', desc_phones[0])
        elif masked_phone and not masked_phone.endswith("*"):
            phone = masked_phone
        else:
            phone = masked_phone

        whatsapp = ""
        raw_wa = str(owner.get("whatsapp_phone") or "")
        if raw_wa and len(re.sub(r'\D', '', raw_wa)) >= 10:
            whatsapp = re.sub(r'\D', '', raw_wa)
            if not whatsapp.startswith("57") and len(whatsapp) == 10:
                whatsapp = "57" + whatsapp
        elif phone and len(phone) == 10 and phone.startswith("3"):
            whatsapp = "57" + phone

        address = str(item.get("address") or f"{neighborhood}, Barranquilla").strip()
        verified = bool(item.get("highlight") or item.get("isMapFeatured") or item.get("showAddress"))

        return {
            "id": prop_id,
            "portal": "Finca Raiz",
            "title": title,
            "property_type": property_type,
            "canon": canon,
            "admin_fee": admin_fee,
            "total_price": total_price,
            "neighborhood": neighborhood,
            "zone": zone,
            "address": address,
            "area_m2": area_m2,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "parking": parking,
            "stratum": stratum,
            "images": images,
            "url": url,
            "contact": {
                "phone": phone,
                "whatsapp": whatsapp,
                "agency": agency,
                "agent_name": agency
            },
            "description": description,
            "verified": verified
        }

    def fetch_neighborhood(
        self,
        barrio_slug: str,
        default_barrio: str = "Barranquilla",
        default_zone: str = "Norte",
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """Fetches a single page of listings for a neighborhood slug."""
        if page == 1:
            url = f"{self.BASE_URL}/arriendo/apartamentos-y-casas/{barrio_slug}/barranquilla"
        else:
            url = f"{self.BASE_URL}/arriendo/apartamentos-y-casas/{barrio_slug}/barranquilla/pagina{page}"

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as resp:
                    if resp.status == 200:
                        html = resp.read().decode("utf-8", errors="ignore")
                        raw_items = self.parse_next_data(html)
                        results = []
                        for itm in raw_items:
                            mapped = self.normalize_property(itm, default_barrio, default_zone)
                            if mapped:
                                results.append(mapped)
                        return results
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed for Finca Raíz '{barrio_slug}' p{page}: {e}")
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)
        return []

    def extract_all(
        self,
        neighborhoods: Optional[List[Tuple[str, str, str]]] = None,
        max_pages: int = 1,
        use_cache_on_failure: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Sweeps target neighborhoods in Barranquilla Norte and collects listings.
        Saves cache on success; falls back to cache on failure.
        """
        barrios = neighborhoods or DEFAULT_TARGET_BARRIOS
        logger.info(f"Starting Finca Raíz extraction across {len(barrios)} target sectors...")

        collected: Dict[str, Dict[str, Any]] = {}

        for slug, barrio, zone in barrios:
            for page in range(1, max_pages + 1):
                try:
                    items = self.fetch_neighborhood(slug, barrio, zone, page=page)
                    for itm in items:
                        collected[itm["id"]] = itm
                except Exception as e:
                    logger.error(f"Error extracting Finca Raíz {slug} page {page}: {e}")
                time.sleep(self.request_delay)

        results = list(collected.values())
        logger.info(f"Finca Raíz live sweep returned {len(results)} qualified properties <= $2.5M COP")

        if results:
            self._save_cache(results)
            return results

        if use_cache_on_failure:
            logger.warning("Finca Raíz live extraction yielded 0 items. Attempting fallback cache...")
            cached = self._load_cache()
            if cached:
                logger.info(f"Loaded {len(cached)} items from Finca Raíz cache.")
                return cached

        return []

    def _save_cache(self, items: List[Dict[str, Any]]) -> None:
        """Saves items to cache file atomically."""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            tmp_path = f"{self.cache_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.cache_path)
            logger.debug(f"Saved {len(items)} items to {self.cache_path}")
        except Exception as e:
            logger.warning(f"Could not save Finca Raíz cache: {e}")

    def _load_cache(self) -> List[Dict[str, Any]]:
        """Loads cached items from file."""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache from {self.cache_path}: {e}")
        return []
