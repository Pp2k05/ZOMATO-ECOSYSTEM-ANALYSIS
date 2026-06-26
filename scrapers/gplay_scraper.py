# =============================================================================
#  scrapers/gplay_scraper.py  —  Google Play Store reviews
# =============================================================================
"""
Uses the `google-play-scraper` library (no API key needed).
Paginates via continuation_token to collect thousands of reviews per app.
"""

import time
import datetime
import logging
from typing import List, Dict

from google_play_scraper import reviews as gp_reviews, Sort

from config import PLAY_STORE_APPS

logger = logging.getLogger(__name__)


def scrape_google_play(target: int) -> List[Dict]:
    """
    Scrape reviews for all apps in PLAY_STORE_APPS.
    *target* is the overall row budget; each app has its own sub-target.
    """
    all_rows: List[Dict] = []

    for app_label, cfg in PLAY_STORE_APPS.items():
        app_id     = cfg["app_id"]
        app_target = cfg["target"]
        product    = cfg["product_tag"]

        logger.info(f"[Play Store] {app_label} ({app_id}) — target {app_target:,}")
        rows = _scrape_app(app_id, app_label, product, app_target)
        logger.info(f"  → {len(rows):,} rows collected")
        all_rows.extend(rows)

        if len(all_rows) >= target:
            break

    logger.info(f"[Play Store] Done — {len(all_rows):,} total rows")
    return all_rows


# ---------------------------------------------------------------------------

def _scrape_app(app_id: str, app_label: str, product_tag: str, target: int) -> List[Dict]:
    rows: List[Dict] = []
    token           = None      # continuation_token for pagination
    batch_size      = 200       # max allowed per call

    while len(rows) < target:
        need = min(batch_size, target - len(rows))
        try:
            result, token = gp_reviews(
                app_id,
                lang="en",
                country="in",
                sort=Sort.NEWEST,
                count=need,
                continuation_token=token,
            )
        except Exception as e:
            logger.warning(f"  Error fetching {app_id}: {e}")
            time.sleep(10)
            break

        if not result:
            break

        for r in result:
            rows.append(_review_to_row(r, app_label, product_tag, app_id))

        logger.info(f"    {app_label}: {len(rows):,}/{target:,} collected")

        if not token:
            break

        time.sleep(1.5)

    return rows[:target]


def _review_to_row(r: dict, app_label: str, product_tag: str, app_id: str) -> Dict:
    date_obj = r.get("at")
    if isinstance(date_obj, datetime.datetime):
        date_str = date_obj.strftime("%d/%m/%Y")
    else:
        date_str = ""

    return {
        "Post_ID":     str(r.get("reviewId", "")),
        "Platform":    "Google Play",
        "Source":      f"Play Store — {app_label}",
        "Date":        date_str,
        "Username":    str(r.get("userName", "")),
        "Title":       str(r.get("title", "") or ""),
        "Text":        str(r.get("content", "") or ""),
        "Score":       r.get("score", ""),
        "Product_Tag": product_tag,
        "URL":         f"https://play.google.com/store/apps/details?id={app_id}",
    }
