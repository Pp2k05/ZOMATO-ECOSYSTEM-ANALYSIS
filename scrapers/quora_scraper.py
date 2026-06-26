# =============================================================================
#  scrapers/quora_scraper.py  —  Quora questions & answers (best-effort)
# =============================================================================
"""
Strategy:
  1. Use DuckDuckGo HTML search to find Quora question URLs for each query.
  2. Fetch each Quora page and parse visible question + answer text.

Quora serves SEO-readable HTML (no JS required) for public answers, making
requests + BeautifulSoup viable without Selenium.  Rate-limit aggressively.
"""

import re
import time
import hashlib
import logging
import datetime
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

from config import QUORA_QUERIES, QUORA_PER_QUERY

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
        "Gecko/20100101 Firefox/124.0"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}
_SESSION = requests.Session()
_SESSION.headers.update(_HEADERS)

_DDG_URL   = "https://html.duckduckgo.com/html/"
_MAX_LINKS = 30   # Quora URLs to collect per query


def scrape_quora(target: int) -> List[Dict]:
    all_rows: List[Dict] = []
    seen_urls: set        = set()

    for query in QUORA_QUERIES:
        if len(all_rows) >= target:
            break
        logger.info(f"[Quora] Query: '{query}'")
        urls = _find_quora_urls(query)
        for url in urls:
            if len(all_rows) >= target:
                break
            if url in seen_urls:
                continue
            seen_urls.add(url)
            rows = _scrape_quora_page(url, query)
            all_rows.extend(rows)
            logger.info(f"  {url}  →  {len(rows)} rows (total: {len(all_rows):,})")
            time.sleep(3)

    logger.info(f"[Quora] Done — {len(all_rows):,} rows")
    return all_rows


# ---------------------------------------------------------------------------

def _find_quora_urls(query: str) -> List[str]:
    """Use DuckDuckGo HTML search to find Quora question URLs."""
    urls: List[str] = []
    params = {
        "q":   f"site:quora.com {query}",
        "kl":  "in-en",
    }
    try:
        resp = _SESSION.post(_DDG_URL, data=params, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if "quora.com" in href:
                # DDG wraps URLs — extract real URL
                real = _extract_real_url(href)
                if real and "quora.com/q/" not in real and real not in urls:
                    urls.append(real)
            if len(urls) >= _MAX_LINKS:
                break
    except Exception as e:
        logger.warning(f"  DDG search error: {e}")
    time.sleep(2)
    return urls


def _extract_real_url(ddg_href: str) -> Optional[str]:
    """Extract the real URL from a DuckDuckGo redirect."""
    match = re.search(r"uddg=(https?[^&]+)", ddg_href)
    if match:
        from urllib.parse import unquote
        return unquote(match.group(1))
    if ddg_href.startswith("https://quora.com") or ddg_href.startswith("https://www.quora.com"):
        return ddg_href
    return None


def _scrape_quora_page(url: str, query: str) -> List[Dict]:
    rows: List[Dict] = []
    try:
        resp = _SESSION.get(url, timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            return rows
        soup = BeautifulSoup(resp.text, "lxml")

        # Extract question title
        title = ""
        title_tag = (
            soup.find("h1")
            or soup.find("span", attrs={"class": re.compile(r"q_text|question_text", re.I)})
        )
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Extract answers — Quora puts answers in divs with long text
        answer_divs = soup.find_all(
            "div",
            attrs={"class": re.compile(r"q-text|spacing_log|answer_content|qu-userSelect", re.I)},
        )
        # Fallback: grab any long <p> blocks
        if not answer_divs:
            answer_divs = [
                p for p in soup.find_all("p")
                if len(p.get_text(strip=True)) > 80
            ]

        for div in answer_divs[:5]:   # max 5 answers per page
            text = div.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 40:
                continue

            uid = hashlib.md5(f"{url}|{text[:100]}".encode()).hexdigest()[:12]
            rows.append({
                "Post_ID":  uid,
                "Platform": "Quora",
                "Source":   "quora.com",
                "Date":     datetime.datetime.utcnow().strftime("%d/%m/%Y"),  # Quora rarely shows dates
                "Username": "",
                "Title":    title,
                "Text":     text,
                "Score":    "",
                "_keyword": query,
                "URL":      url,
            })

    except Exception as e:
        logger.warning(f"  Quora page error ({url}): {e}")

    return rows
