# =============================================================================
#  scrapers/twitter_scraper.py  —  Unofficial Twitter/X scraper via ntscraper
# =============================================================================
"""
Uses ntscraper (Python 3.13 compatible, no API key required).
ntscraper scrapes Twitter's Nitter frontend which mirrors public tweets.
Falls back gracefully if blocked; every row is flagged Source="Twitter".
"""

import datetime
import logging
import time
from typing import List, Dict

from config import TWITTER_QUERIES, TWITTER_MONTHS_BACK, TWITTER_PER_QUERY

logger = logging.getLogger(__name__)


def scrape_twitter(target: int) -> List[Dict]:
    all_rows: List[Dict] = []

    try:
        from ntscraper import Nitter
    except ImportError:
        logger.error("[Twitter] ntscraper not installed. Run: pip install ntscraper")
        return []

    since_date = (
        datetime.datetime.utcnow() - datetime.timedelta(days=TWITTER_MONTHS_BACK * 30)
    )

    # Try a few Nitter instances — some may be down
    nitter_instances = [
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
        "https://nitter.1d4.us",
        "https://nitter.unixfox.eu",
    ]

    scraper = None
    for instance in nitter_instances:
        try:
            scraper = Nitter(log_level=1, skip_instance_check=True)
            # test with a quick query
            test = scraper.get_tweets("Zomato", mode="term", number=2, instance=instance)
            if test and test.get("tweets"):
                logger.info(f"[Twitter] Using Nitter instance: {instance}")
                break
        except Exception as e:
            logger.warning(f"  Nitter instance {instance} failed: {e}")
            scraper = None
            time.sleep(2)

    if scraper is None:
        logger.warning("[Twitter] All Nitter instances failed — skipping Twitter source")
        return []

    for query in TWITTER_QUERIES:
        if len(all_rows) >= target:
            break

        logger.info(f"[Twitter] query: '{query}' — target {TWITTER_PER_QUERY}")
        count = 0

        try:
            results = scraper.get_tweets(
                query,
                mode="term",
                number=TWITTER_PER_QUERY,
                since=since_date.strftime("%Y-%m-%d"),
            )
            tweets = results.get("tweets", []) if results else []

            for tweet in tweets:
                if count >= TWITTER_PER_QUERY or len(all_rows) >= target:
                    break
                row = _tweet_to_row(tweet, query)
                if row and row.get("Text"):
                    all_rows.append(row)
                    count += 1

        except Exception as e:
            logger.warning(f"  Twitter error on '{query}': {e}")
            time.sleep(5)
            continue

        logger.info(f"  → {count} tweets for '{query}' (total: {len(all_rows):,})")
        time.sleep(3)

    logger.info(f"[Twitter] Done — {len(all_rows):,} rows")
    return all_rows


def _tweet_to_row(tweet: dict, query: str) -> Dict:
    try:
        # ntscraper field names
        date_str   = _parse_date(tweet.get("date", ""))
        text       = tweet.get("text", "") or tweet.get("content", "")
        tweet_id   = tweet.get("tweet-id", tweet.get("id", ""))
        username   = tweet.get("user", {}).get("username", "") if isinstance(tweet.get("user"), dict) else ""
        likes      = _safe_int(tweet.get("stats", {}).get("likes", 0) if isinstance(tweet.get("stats"), dict) else tweet.get("likes", 0))
        url        = tweet.get("link", tweet.get("url", ""))

        return {
            "Post_ID":     str(tweet_id),
            "Platform":    "Twitter",
            "Source":      "Twitter (unofficial)",
            "Date":        date_str,
            "Username":    str(username),
            "Title":       "",
            "Text":        str(text),
            "Score":       likes,
            "_keyword":    query,
            "URL":         str(url),
        }
    except Exception as e:
        logger.warning(f"  Failed to parse tweet: {e}")
        return {}


def _parse_date(date_val) -> str:
    if not date_val:
        return ""
    if isinstance(date_val, datetime.datetime):
        return date_val.strftime("%d/%m/%Y")
    s = str(date_val)
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%b %d, %Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s[:19], fmt[:len(s[:19])]).strftime("%d/%m/%Y")
        except Exception:
            pass
    return s[:10]


def _safe_int(val) -> int:
    try:
        return int(str(val).replace(",", "").strip())
    except Exception:
        return 0
