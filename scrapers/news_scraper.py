# =============================================================================
#  scrapers/news_scraper.py  —  News article comments (best-effort)
# =============================================================================
"""
Strategy:
  1. DuckDuckGo → find article URLs per site per keyword.
  2. Fetch article page, try to extract comment section HTML.
  3. For Disqus-powered sites: hit Disqus embed iframe src → extract comments.
  4. For others: parse visible comment blocks via BeautifulSoup.

Sites targeted: Economic Times, Times of India, Moneycontrol, YourStory.
"""

import re
import time
import hashlib
import logging
import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urljoin, urlparse
from typing import List, Dict, Optional

from config import NEWS_SOURCES, NEWS_QUERIES, NEWS_PER_QUERY

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}
_SESSION = requests.Session()
_SESSION.headers.update(_HEADERS)

_DDG_URL   = "https://html.duckduckgo.com/html/"
_MAX_ARTICLES_PER_QUERY = 8


def scrape_news(target: int) -> List[Dict]:
    all_rows: List[Dict] = []
    seen_ids: set         = set()

    for site_name, site_cfg in NEWS_SOURCES.items():
        for query in NEWS_QUERIES:
            if len(all_rows) >= target:
                break
            logger.info(f"[News] {site_name} | '{query}'")
            urls = _find_article_urls(query, site_cfg["domain"])
            for url in urls:
                if len(all_rows) >= target:
                    break
                comments = _extract_comments(url, site_name, query, seen_ids)
                all_rows.extend(comments)
                if comments:
                    logger.info(f"  {url[-60:]}  →  {len(comments)} comments (total: {len(all_rows):,})")
                time.sleep(3)

    logger.info(f"[News] Done — {len(all_rows):,} rows")
    return all_rows


# ---------------------------------------------------------------------------

def _find_article_urls(query: str, domain: str) -> List[str]:
    """DuckDuckGo → article URLs on the given domain."""
    urls: List[str] = []
    params = {"q": f"site:{domain} {query}", "kl": "in-en"}
    try:
        resp = _SESSION.post(_DDG_URL, data=params, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            real = _unwrap_ddg(href)
            if real and domain in real and real not in urls:
                urls.append(real)
            if len(urls) >= _MAX_ARTICLES_PER_QUERY:
                break
    except Exception as e:
        logger.warning(f"  DDG error: {e}")
    time.sleep(2)
    return urls


def _unwrap_ddg(href: str) -> Optional[str]:
    m = re.search(r"uddg=(https?[^&]+)", href)
    if m:
        return unquote(m.group(1))
    if href.startswith("http"):
        return href
    return None


def _extract_comments(url: str, site_name: str, query: str, seen: set) -> List[Dict]:
    rows: List[Dict] = []
    try:
        resp = _SESSION.get(url, timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            return rows
        soup = BeautifulSoup(resp.text, "lxml")

        # Try Disqus embed
        disqus_rows = _try_disqus(soup, url, site_name, query, seen)
        if disqus_rows:
            return disqus_rows

        # Generic comment selectors (various CMS patterns)
        comment_selectors = [
            "div.comment-body", "div.comment-text", "div.comment-content",
            "p.comment", "li.comment", "div[class*='comment']",
            "div.user-comment", "span.comment", "div.post-comment",
            ".comments-list .comment", ".commentsWrapper p",
        ]
        for selector in comment_selectors:
            blocks = soup.select(selector)
            for block in blocks[:NEWS_PER_QUERY]:
                text = block.get_text(separator=" ", strip=True)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) < 20:
                    continue
                uid = hashlib.md5(f"{url}|{text[:80]}".encode()).hexdigest()[:12]
                if uid in seen:
                    continue
                seen.add(uid)
                # Try to find a username nearby
                username = _extract_username_near(block)
                rows.append({
                    "Post_ID":  uid,
                    "Platform": "News",
                    "Source":   site_name,
                    "Date":     datetime.datetime.utcnow().strftime("%d/%m/%Y"),
                    "Username": username,
                    "Title":    _get_article_title(soup),
                    "Text":     text,
                    "Score":    "",
                    "_keyword": query,
                    "URL":      url,
                })
            if rows:
                break

    except Exception as e:
        logger.warning(f"  News scrape error ({url}): {e}")
    return rows


def _try_disqus(soup: BeautifulSoup, page_url: str, site_name: str, query: str, seen: set) -> List[Dict]:
    """Attempt to find Disqus iframe and load its comments via Disqus API."""
    rows: List[Dict] = []
    # Look for Disqus script or identifier
    disqus_script = soup.find("script", string=re.compile(r"disqus_shortname|disqus\.com", re.I))
    shortname = None
    if disqus_script:
        m = re.search(r"disqus_shortname\s*=\s*['\"]([^'\"]+)['\"]", disqus_script.string or "")
        if m:
            shortname = m.group(1)

    # Also check for var DISQUS config
    for script in soup.find_all("script"):
        txt = script.string or ""
        m = re.search(r"this\.page\.identifier\s*=\s*['\"]([^'\"]+)['\"]", txt)
        if m and shortname:
            thread_id = m.group(1)
            rows = _fetch_disqus_comments(shortname, thread_id, page_url, site_name, query, seen)
            if rows:
                return rows
    return rows


def _fetch_disqus_comments(shortname: str, thread_id: str, page_url: str,
                            site_name: str, query: str, seen: set) -> List[Dict]:
    """Fetch comments via the public Disqus API (no API key for basic listing)."""
    rows: List[Dict] = []
    # Disqus public endpoint (no auth required for public forums)
    api_url = (
        f"https://disqus.com/api/3.0/threads/listPosts.json"
        f"?forum={shortname}&thread:ident={thread_id}&limit=50"
        f"&api_key=E8Hts8uAXE3HWFCkAXhBcTlFmefAEMEMGYuuuLgc4VBdbMf0dQbr9lc8jqBdcC0o"
    )
    try:
        resp = requests.get(api_url, timeout=15)
        if resp.status_code != 200:
            return rows
        data = resp.json()
        for post in data.get("response", []):
            text = BeautifulSoup(post.get("raw_message", ""), "lxml").get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) < 10:
                continue
            uid = str(post.get("id", ""))
            if uid in seen:
                continue
            seen.add(uid)
            created = post.get("createdAt", "")
            date_str = ""
            if created:
                try:
                    date_str = datetime.datetime.fromisoformat(created.replace("T", " ").split("+")[0]).strftime("%d/%m/%Y")
                except Exception:
                    date_str = created[:10]
            rows.append({
                "Post_ID":  uid,
                "Platform": "News",
                "Source":   site_name,
                "Date":     date_str,
                "Username": post.get("author", {}).get("name", ""),
                "Title":    "",
                "Text":     text,
                "Score":    post.get("likes", 0),
                "_keyword": query,
                "URL":      page_url,
            })
    except Exception as e:
        logger.warning(f"  Disqus API error: {e}")
    return rows


def _get_article_title(soup: BeautifulSoup) -> str:
    tag = soup.find("h1") or soup.find("title")
    return tag.get_text(strip=True) if tag else ""


def _extract_username_near(block) -> str:
    """Try to find a username/author in sibling/parent elements."""
    for selector in ["span.author", "span.name", "a.username", "div.author", ".comment-author"]:
        parent = block.parent
        if parent:
            found = parent.select_one(selector)
            if found:
                return found.get_text(strip=True)
    return ""
