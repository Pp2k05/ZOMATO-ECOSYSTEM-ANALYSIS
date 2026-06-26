# =============================================================================
#  scrapers/linkedin_scraper.py  --  LinkedIn posts via DuckDuckGo/Google search
# =============================================================================
"""
LinkedIn blocks direct scraping. This scraper uses DuckDuckGo search to find
LinkedIn posts mentioning Zomato/Blinkit/District and extracts the preview text
visible in search results (no login needed).

Search query: site:linkedin.com/posts "Zomato" OR "Blinkit" etc.
"""

import time
import datetime
import logging
import requests
import hashlib
from bs4 import BeautifulSoup
from typing import List, Dict

logger = logging.getLogger(__name__)

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
})

# Search queries to cover all 3 brands
SEARCH_QUERIES = [
    # Zomato
    'site:linkedin.com/posts "Zomato" food delivery India',
    'site:linkedin.com/posts "Zomato" refund customer experience',
    'site:linkedin.com/posts "Zomato Gold" membership',
    'site:linkedin.com/posts "Zomato" restaurant partner',
    'site:linkedin.com/posts "Zomato" delivery experience India',
    'site:linkedin.com/posts "Zomato" app review',
    'site:linkedin.com/posts Zomato India startup',
    'site:linkedin.com/posts Zomato Deepinder Goyal',
    # Blinkit
    'site:linkedin.com/posts "Blinkit" quick commerce India',
    'site:linkedin.com/posts "Blinkit" 10 minute delivery',
    'site:linkedin.com/posts "Blinkit" grocery delivery review',
    'site:linkedin.com/posts "Blinkit" inventory dark store',
    'site:linkedin.com/posts Blinkit Albinder Dhindsa',
    # District
    'site:linkedin.com/posts "District" Zomato events experiences',
    'site:linkedin.com/posts "District by Zomato" app',
    'site:linkedin.com/posts "District" live events India app',
    # General
    'site:linkedin.com/posts Zomato Blinkit foodtech India',
    'site:linkedin.com/posts HyperPure Zomato restaurant',
]


def scrape_linkedin(target: int) -> List[Dict]:
    rows     : List[Dict] = []
    seen_urls: set        = set()

    logger.info(f"[LinkedIn] Target: {target:,} posts via search")

    for query in SEARCH_QUERIES:
        if len(rows) >= target:
            break
        logger.info(f"  Query: {query[:70]}")

        # Try DuckDuckGo first, then Bing
        results = _ddg_search(query) or _bing_search(query)

        for item in results:
            url  = item.get("url", "")
            text = item.get("text", "").strip()
            if not url or not text or url in seen_urls:
                continue
            if len(text) < 30:
                continue

            seen_urls.add(url)
            pid = hashlib.md5(url.encode()).hexdigest()[:12]

            # Infer brand
            tl = text.lower() + url.lower()
            if "blinkit" in tl:
                tag = "Blinkit"
            elif "district" in tl:
                tag = "District"
            else:
                tag = "Zomato"

            rows.append({
                "Post_ID":     pid,
                "Platform":    "LinkedIn",
                "Source":      "LinkedIn",
                "Date":        item.get("date", ""),
                "Username":    item.get("author", ""),
                "Title":       item.get("title", "")[:200],
                "Text":        text[:2000],
                "Score":       "",
                "Product_Tag": tag,
                "URL":         url,
                "_keyword":    "LinkedIn",
            })

        time.sleep(2.5)

    logger.info(f"[LinkedIn] Done - {len(rows):,} posts")
    return rows[:target]


# ---------------------------------------------------------------------------
# DuckDuckGo search
# ---------------------------------------------------------------------------

def _ddg_search(query: str) -> List[Dict]:
    results = []
    try:
        resp = _SESSION.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "in-en"},
            timeout=20
        )
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        for result in soup.select(".result"):
            a_tag   = result.select_one(".result__a")
            snippet = result.select_one(".result__snippet")
            if not a_tag:
                continue
            url  = a_tag.get("href", "")
            if "linkedin.com" not in url:
                continue
            text = snippet.get_text(strip=True) if snippet else ""
            results.append({
                "url":    url,
                "title":  a_tag.get_text(strip=True),
                "text":   text,
                "author": "",
                "date":   "",
            })
    except Exception as e:
        logger.warning(f"  DDG error: {e}")
    return results


# ---------------------------------------------------------------------------
# Bing search fallback
# ---------------------------------------------------------------------------

def _bing_search(query: str) -> List[Dict]:
    results = []
    try:
        resp = _SESSION.get(
            "https://www.bing.com/search",
            params={"q": query, "count": 20, "mkt": "en-IN"},
            timeout=20
        )
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        for li in soup.select("li.b_algo"):
            a_tag   = li.select_one("h2 a")
            snippet = li.select_one(".b_caption p")
            if not a_tag:
                continue
            url = a_tag.get("href", "")
            if "linkedin.com" not in url:
                continue
            text = snippet.get_text(strip=True) if snippet else ""
            results.append({
                "url":    url,
                "title":  a_tag.get_text(strip=True),
                "text":   text,
                "author": "",
                "date":   "",
            })
    except Exception as e:
        logger.warning(f"  Bing error: {e}")
    return results
