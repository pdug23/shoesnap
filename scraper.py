"""Running Warehouse shoe image scraper using SeleniumBase UC Mode."""

import time
import random
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from seleniumbase import SB


@dataclass
class ShoeResult:
    search_term: str
    product_name: str
    image_url: str
    product_url: str
    thumbnail: bytes | None = None


class ShoeScraper:
    BASE_URL = "https://www.runningwarehouse.com"
    SEARCH_URL = BASE_URL + "/searchresult.html?search={}"

    def __init__(self, headless=True):
        self.headless = headless

    def scrape_shoes(self, shoe_names: list[str], progress_callback=None) -> list[ShoeResult]:
        """Scrape Running Warehouse for shoe images.

        Args:
            shoe_names: List of shoe names to search for.
            progress_callback: Optional callable(current, total, message) for progress updates.
        """
        results = []

        with SB(uc=True, headless=self.headless, headed=not self.headless) as sb:
            for i, name in enumerate(shoe_names):
                if progress_callback:
                    progress_callback(i, len(shoe_names), f"Searching: {name}")

                try:
                    found = self._search_shoe(sb, name)
                    results.extend(found)
                except Exception as e:
                    if progress_callback:
                        progress_callback(i, len(shoe_names), f"Error searching '{name}': {e}")

                # Random delay to avoid rate limiting
                if i < len(shoe_names) - 1:
                    time.sleep(random.uniform(1.5, 3.0))

        if progress_callback:
            progress_callback(len(shoe_names), len(shoe_names), "Scraping complete")

        return results

    def _search_shoe(self, sb, shoe_name: str) -> list[ShoeResult]:
        """Search for a single shoe and extract results."""
        url = self.SEARCH_URL.format(quote_plus(shoe_name))
        sb.uc_open_with_reconnect(url, reconnect_time=4)

        # Wait for page content to load
        time.sleep(2)

        results = []

        # Try multiple selector strategies for product listings
        selectors = [
            "div.product_wrapper",
            "div[class*='product']",
            "div.search-result-item",
            "a[href*='descpage']",
        ]

        products = []
        for sel in selectors:
            try:
                products = sb.find_elements(sel)
                if products:
                    break
            except Exception:
                continue

        if not products:
            # Fallback: try to find any links to product pages with images
            try:
                products = sb.find_elements("a[href*='descpage']")
            except Exception:
                pass

        if not products:
            # Last resort: grab all images that look like product images
            try:
                all_links = sb.find_elements("a[href*='.html']")
                all_imgs = sb.find_elements("img[src*='shoe'], img[src*='product'], img[src*='jpg']")
                # Try to pair them
                for img in all_imgs[:20]:
                    try:
                        src = img.get_attribute("src") or img.get_attribute("data-src") or ""
                        alt = img.get_attribute("alt") or ""
                        if src and ("shoe" in src.lower() or "product" in src.lower() or alt):
                            parent = img.find_element("xpath", "./..")
                            href = parent.get_attribute("href") or ""
                            results.append(ShoeResult(
                                search_term=shoe_name,
                                product_name=alt or shoe_name,
                                image_url=self._make_absolute(src),
                                product_url=self._make_absolute(href),
                            ))
                    except Exception:
                        continue
            except Exception:
                pass
            return results

        for product in products[:20]:  # Cap at 20 results per search
            try:
                result = self._extract_product(sb, product, shoe_name)
                if result:
                    results.append(result)
            except Exception:
                continue

        return results

    def _extract_product(self, sb, element, search_term: str) -> ShoeResult | None:
        """Extract shoe data from a product element."""
        # Try to find the image
        img_url = None
        product_name = None
        product_url = None

        # Look for image
        try:
            img = element.find_element("tag name", "img")
            img_url = img.get_attribute("src") or img.get_attribute("data-src")
            product_name = img.get_attribute("alt")
        except Exception:
            pass

        # Look for link
        try:
            tag_name = element.tag_name
            if tag_name == "a":
                product_url = element.get_attribute("href")
                if not product_name:
                    product_name = element.get_attribute("title") or element.text.strip()
            else:
                link = element.find_element("tag name", "a")
                product_url = link.get_attribute("href")
                if not product_name:
                    product_name = link.get_attribute("title") or link.text.strip()
        except Exception:
            pass

        # Look for product name in text if still missing
        if not product_name:
            try:
                name_el = element.find_element("css selector", "[class*='name'], [class*='title'], h2, h3, span")
                product_name = name_el.text.strip()
            except Exception:
                product_name = search_term

        if not img_url:
            return None

        return ShoeResult(
            search_term=search_term,
            product_name=product_name or search_term,
            image_url=self._make_absolute(img_url),
            product_url=self._make_absolute(product_url or ""),
        )

    def _make_absolute(self, url: str) -> str:
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.BASE_URL + url
        if not url.startswith("http"):
            return self.BASE_URL + "/" + url
        return url
