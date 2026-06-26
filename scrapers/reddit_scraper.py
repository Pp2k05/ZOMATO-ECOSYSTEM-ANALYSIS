# =============================================================================
#  scrapers/reddit_scraper.py  --  Reddit via Arctic Shift API
# =============================================================================
"""
Uses Arctic Shift (arctic-shift.photon-reddit.com) -- public, no auth needed.
- Post search: title= param (confirmed working)
- Comments: skipped gracefully (endpoint returns 400/403 in current environment)
- Posts alone contain full text which is sufficient for analysis
"""

import time
import datetime
import logging
import requests
from typing import List, Dict, Optional

from config import (
    SUBREDDITS, KEYWORDS, REDDIT_MONTHS_BACK, REDDIT_COMMENTS_PER_POST
)

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}
_SESSION = requests.Session()
_SESSION.headers.update(_HEADERS)

_AS_POSTS = "https://arctic-shift.photon-reddit.com/api/posts/search"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scrape_reddit(target: int) -> List[Dict]:
    cutoff_dt  = datetime.datetime.utcnow() - datetime.timedelta(days=REDDIT_MONTHS_BACK * 30)
    cutoff_ts  = int(cutoff_dt.timestamp())
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_rows : List[Dict] = []
    seen_ids : set        = set()

    logger.info(f"[Reddit] Target: {target:,} | cutoff: {REDDIT_MONTHS_BACK} months back")

    for sub in SUBREDDITS:
        if len(all_rows) >= target:
            break
        for kw in KEYWORDS:
            if len(all_rows) >= target:
                break
            logger.info(f"  r/{sub} | '{kw}' | rows: {len(all_rows):,}")
            posts = _fetch_posts(sub, kw, cutoff_iso, cutoff_ts, seen_ids)
            for post in posts:
                if len(all_rows) >= target:
                    break
                row = _post_to_row(post, sub, kw)
                if row:
                    all_rows.append(row)
                    seen_ids.add(post.get("id", ""))

    logger.info(f"[Reddit] Done - {len(all_rows):,} rows")
    return all_rows


# ---------------------------------------------------------------------------
# Fetch posts via Arctic Shift
# ---------------------------------------------------------------------------

def _fetch_posts(sub: str, keyword: str, cutoff_iso: str, cutoff_ts: int,
                 seen_ids: set) -> List[Dict]:
    posts: List[Dict] = []

    # Page 1: search with after= cutoff
    params: Dict = {
        "subreddit": sub,
        "title":     keyword,
        "limit":     100,
        "after":     cutoff_iso,
        "sort":      "desc",
    }

    data = _get_json(_AS_POSTS, params, delay=1.2)
    if not data:
        return posts

    items = data.get("data", []) or []
    for item in items:
        pid = item.get("id", "")
        ts  = _parse_ts(item.get("created_utc", 0))
        if ts < cutoff_ts:
            continue
        if pid and pid not in seen_ids:
            posts.append(item)

    # Page 2+: paginate using before= last post's timestamp (ISO)
    if items:
        last_ts_raw = items[-1].get("created_utc", "")
        last_iso    = _to_iso(last_ts_raw)
        if last_iso and len(items) == 100:
            params2 = {
                "subreddit": sub,
                "title":     keyword,
                "limit":     100,
                "before":    last_iso,
                "after":     cutoff_iso,
                "sort":      "desc",
            }
            for _page in range(4):    # up to 4 more pages = 500 posts per kw/sub
                data2 = _get_json(_AS_POSTS, params2, delay=1.2)
                if not data2:
                    break
                items2 = data2.get("data", []) or []
                if not items2:
                    break
                added = 0
                for item in items2:
                    pid = item.get("id", "")
                    ts  = _parse_ts(item.get("created_utc", 0))
                    if ts < cutoff_ts:
                        break
                    if pid and pid not in seen_ids:
                        posts.append(item)
                        added += 1
                if added == 0 or len(items2) < 100:
                    break
                last_iso2 = _to_iso(items2[-1].get("created_utc", ""))
                if not last_iso2:
                    break
                params2["before"] = last_iso2
                time.sleep(1.0)

    return posts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_to_row(post: Dict, sub: str, keyword: str) -> Optional[Dict]:
    title = (post.get("title") or "").strip()
    text  = (post.get("selftext") or post.get("body") or "").strip()
    if text in ("[deleted]", "[removed]"):
        text = ""
    body  = text or title
    if not body:
        return None
    ts    = post.get("created_utc", "")
    pid   = post.get("id", "")
    return {
        "Post_ID":  pid,
        "Platform": "Reddit",
        "Source":   sub,
        "Date":     _fmt_date(ts),
        "Username": str(post.get("author", "")),
        "Title":    title,
        "Text":     body,
        "Score":    post.get("score", 0),
        "_keyword": keyword,
        "URL":      f"https://www.reddit.com/r/{sub}/comments/{pid}/",
    }


def _get_json(url: str, params: dict, delay: float = 1.0):
    for attempt in range(3):
        try:
            resp = _SESSION.get(url, params=params, timeout=25)
            if resp.status_code == 429:
                wait = 20 * (attempt + 1)
                logger.warning(f"  Rate-limited - sleeping {wait}s")
                time.sleep(wait)
                continue
            if resp.status_code == 200:
                time.sleep(delay)
                return resp.json()
            logger.warning(f"  HTTP {resp.status_code} - {url[:60]}")
            return None
        except Exception as e:
            logger.warning(f"  Request error: {e}")
            time.sleep(5)
    return None


def _parse_ts(val) -> int:
    try:
        if isinstance(val, (int, float)):
            return int(val)
        s = str(val)
        if "T" in s:
            return int(datetime.datetime.fromisoformat(
                s.replace("Z", "+00:00")).timestamp())
        return int(float(s))
    except Exception:
        return 0


def _to_iso(val) -> str:
    ts = _parse_ts(val)
    if ts <= 0:
        return ""
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_date(ts) -> str:
    t = _parse_ts(ts)
    if t <= 0:
        return ""
    return datetime.datetime.utcfromtimestamp(t).strftime("%d/%m/%Y")
