# =============================================================================
#  scrapers/appstore_scraper.py  —  Apple App Store reviews (direct RSS/JSON)
# =============================================================================
"""
Uses Apple's public iTunes RSS feed and Search API directly.
No third-party library needed — pure requests + json.

Apple caps the RSS feed at 500 reviews per page; we paginate across
multiple pages (up to 10) and multiple countries to maximise yield.
Endpoint: https://itunes.apple.com/{country}/rss/customerreviews/
          page={page}/id={app_id}/sortby=mostrecent/json
"""

import json
import time
import datetime
import logging
import requests
from typing import List, Dict

from config import APP_STORE_APPS, APP_STORE_COUNTRIES

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept": "application/json",
}
_SESSION = requests.Session()
_SESSION.headers.update(_HEADERS)

_RSS_URL = (
    "https://itunes.apple.com/{country}/rss/customerreviews/"
    "page={page}/id={app_id}/sortby=mostrecent/json"
)


def scrape_app_store(target: int) -> List[Dict]:
    all_rows: List[Dict] = []

    for app_label, cfg in APP_STORE_APPS.items():
        app_target  = cfg["target"]
        product_tag = cfg["product_tag"]

        logger.info(
            f"[App Store] {app_label} (id={cfg['app_id']}) — target {app_target:,}"
        )
        rows = _scrape_app(cfg, app_label, product_tag, app_target)
        logger.info(f"  → {len(rows):,} rows collected")
        all_rows.extend(rows)

        if len(all_rows) >= target:
            break

    logger.info(f"[App Store] Done — {len(all_rows):,} total rows")
    return all_rows


# ---------------------------------------------------------------------------

def _scrape_app(cfg: dict, app_label: str, product_tag: str, target: int) -> List[Dict]:
    seen_ids: set    = set()
    rows: List[Dict] = []

    for country in APP_STORE_COUNTRIES:
        if len(rows) >= target:
            break

        logger.info(f"    {app_label} [{country.upper()}] — collected {len(rows):,}/{target:,}")

        for page in range(1, 11):   # Apple serves up to 10 pages of 50 reviews each
            if len(rows) >= target:
                break

            url = _RSS_URL.format(country=country, page=page, app_id=cfg["app_id"])
            try:
                resp = _SESSION.get(url, timeout=20)
                if resp.status_code == 404:
                    break   # no more pages for this country
                if resp.status_code != 200:
                    logger.warning(f"      HTTP {resp.status_code} — {url}")
                    break

                data = resp.json()
                entries = data.get("feed", {}).get("entry", [])

                # First entry is app metadata, not a review
                if entries and "im:name" in entries[0]:
                    entries = entries[1:]

                if not entries:
                    break

                for entry in entries:
                    review_id = entry.get("id", {}).get("label", "") + country
                    if review_id in seen_ids:
                        continue
                    seen_ids.add(review_id)

                    row = _entry_to_row(entry, app_label, product_tag, cfg["app_id"])
                    if row:
                        rows.append(row)

                    if len(rows) >= target:
                        break

                logger.info(f"      page {page}: +{len(entries)} → total {len(rows):,}")

            except Exception as e:
                logger.warning(f"      Error page {page}/{country}: {e}")
                break

            time.sleep(1)

        time.sleep(2)

    return rows[:target]


def _entry_to_row(entry: dict, app_label: str, product_tag: str, app_id: str) -> Dict:
    try:
        title    = entry.get("title", {}).get("label", "")
        text     = entry.get("content", {}).get("label", "")
        if not text:
            text = entry.get("summary", {}).get("label", "")
        rating   = entry.get("im:rating", {}).get("label", "")
        author   = entry.get("author", {}).get("name", {}).get("label", "")
        updated  = entry.get("updated", {}).get("label", "")  # ISO format
        review_id = entry.get("id", {}).get("label", "")
        link     = entry.get("link", {}).get("attributes", {}).get("href", 
                    f"https://apps.apple.com/app/id{app_id}")

        date_str = ""
        if updated:
            try:
                date_str = datetime.datetime.fromisoformat(
                    updated.replace("Z", "+00:00")
                ).strftime("%d/%m/%Y")
            except Exception:
                date_str = updated[:10]

        if not text and not title:
            return None

        return {
            "Post_ID":     str(review_id),
            "Platform":    "Apple App Store",
            "Source":      f"App Store — {app_label}",
            "Date":        date_str,
            "Username":    str(author),
            "Title":       str(title),
            "Text":        str(text),
            "Score":       str(rating),
            "Product_Tag": product_tag,
            "URL":         str(link),
        }
    except Exception as e:
        logger.warning(f"  Entry parse error: {e}")
        return None
