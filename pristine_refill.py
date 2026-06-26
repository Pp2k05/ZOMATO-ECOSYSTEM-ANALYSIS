"""
pristine_refill_v2.py
=====================
Scrubs all 3 datasets and refills from Play Store + App Store + Reddit.
Rules:
  - Zomato / Blinkit : Only reviews >= 01/12/2025
  - District         : No date restriction (app too new)
  - ALL 3            : Zero text duplicates, enforced via a shared seen_texts set
                       across ALL sources for each brand.
"""

import os, sys, time, json, subprocess, datetime, requests, logging
import pandas as pd
from google_play_scraper import reviews as gp_reviews, Sort

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler("pristine_v2.log", encoding="utf-8")])
logger = logging.getLogger(__name__)

CUTOFF_DATE = pd.to_datetime("2025-12-01")

BRANDS = {
    "Zomato":  {"file": "zomato_data_enriched.xlsx",  "target": 25000,
                "play_id": "com.application.zomato",  "app_id": "434613896",
                "date_restrict": True},
    "Blinkit": {"file": "blinkit_data_enriched.xlsx", "target": 20000,
                "play_id": "com.grofers.customerapp", "app_id": "960335206",
                "date_restrict": True},
    "District":{"file": "district_data_enriched.xlsx","target": 10000,
                "play_id": "com.application.zomato.district", "app_id": "6670536058",
                "date_restrict": False},
}

APP_STORE_COUNTRIES = [
    "in","us","gb","au","ca","sg","ae","nz","za","my",
    "ph","id","lk","bd","np","pk","sa","qa","kw","om","bh",
    "ie","de","fr","nl","se","ch","no","dk","fi"
]

REDDIT_SUBREDDITS = [
    "zomato","blinkit","india","bangalore","mumbai","delhi","hyderabad",
    "chennai","pune","FoodIndia","IndianFood","GoodiesInIndia","IndiaSocial"
]
REDDIT_KEYWORDS_MAP = {
    "Zomato":   ["zomato","zomato delivery","zomato food","zomato review","zomato experience"],
    "Blinkit":  ["blinkit","blinkit delivery","grofers","blinkit review","quick commerce"],
    "District": ["district app","district tickets","district zomato","district events","district booking"],
}

# ─────────────────────────── helpers ──────────────────────────────────────────

def is_valid_date(dt_obj, date_restrict):
    """Returns True if we should keep this date."""
    if not date_restrict:
        return True
    if dt_obj is None:
        return False
    return pd.to_datetime(dt_obj) >= CUTOFF_DATE

def clean_text(t):
    return str(t).strip() if t else ""

# ─────────────────────────── Play Store ───────────────────────────────────────

def scrape_play(brand, play_id, needed, seen_texts, seen_ids, date_restrict):
    logger.info(f"  [Play Store] {brand} — need {needed:,}")
    rows, token = [], None
    stalled = 0

    while len(rows) < needed:
        try:
            res, token = gp_reviews(play_id, lang="en", country="in",
                                    sort=Sort.NEWEST, count=199,
                                    continuation_token=token)
        except Exception as e:
            logger.warning(f"  Play Store error: {e}")
            break
        if not res:
            break

        added = 0
        for r in res:
            rid  = str(r.get("reviewId",""))
            text = clean_text(r.get("content",""))
            dt   = r.get("at")

            if not is_valid_date(dt, date_restrict):
                stalled += 1
                continue
            stalled = 0

            if not text or text in seen_texts or rid in seen_ids:
                continue

            seen_ids.add(rid);  seen_texts.add(text)
            date_str = dt.strftime("%d/%m/%Y") if dt else ""
            rows.append({
                "Review_ID": rid, "Platform": "Google Play Store",
                "Source": "Play Store", "Date": date_str,
                "Username": r.get("userName",""), "Title": "Play Store Review",
                "Text": text, "Score": r.get("score",""),
                "Product_Tag": brand,
                "URL": f"https://play.google.com/store/apps/details?id={play_id}"
            })
            added += 1
            if len(rows) >= needed:
                break

        logger.info(f"    +{added} → {len(rows):,}/{needed:,}")
        if stalled > 2000:
            logger.info("    Exhausted date-filtered reviews from Play Store.")
            break
        if not token:
            break

    return pd.DataFrame(rows)


# ─────────────────────────── App Store ────────────────────────────────────────

_AS_SESSION = requests.Session()
_AS_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Accept": "application/json"
})

def scrape_appstore(brand, app_id, needed, seen_texts, seen_ids, date_restrict):
    logger.info(f"  [App Store] {brand} — need {needed:,}")
    rows = []

    for cc in APP_STORE_COUNTRIES:
        if len(rows) >= needed:
            break
        for page in range(1, 11):
            if len(rows) >= needed:
                break
            url = (f"https://itunes.apple.com/{cc}/rss/customerreviews/"
                   f"page={page}/id={app_id}/sortby=mostrecent/json")
            try:
                resp = _AS_SESSION.get(url, timeout=20)
                if resp.status_code == 404:
                    break
                if resp.status_code != 200:
                    break
                entries = resp.json().get("feed",{}).get("entry",[])
                # first entry is app metadata
                if entries and "im:name" in entries[0]:
                    entries = entries[1:]
                if not entries:
                    break

                added = 0
                for entry in entries:
                    text     = clean_text(entry.get("content",{}).get("label","") or
                                          entry.get("summary",{}).get("label",""))
                    title    = clean_text(entry.get("title",{}).get("label",""))
                    body     = text or title
                    updated  = entry.get("updated",{}).get("label","")
                    rid      = str(entry.get("id",{}).get("label","")) + cc

                    # Date check
                    dt_obj = None
                    date_str = ""
                    if updated:
                        try:
                            dt_obj = datetime.datetime.fromisoformat(updated.replace("Z","+00:00"))
                            date_str = dt_obj.strftime("%d/%m/%Y")
                        except Exception:
                            pass

                    if not is_valid_date(dt_obj, date_restrict):
                        continue
                    if not body or body in seen_texts or rid in seen_ids:
                        continue

                    seen_ids.add(rid);  seen_texts.add(body)
                    rows.append({
                        "Review_ID": rid, "Platform": "Apple App Store",
                        "Source": f"App Store — {cc.upper()}", "Date": date_str,
                        "Username": clean_text(entry.get("author",{}).get("name",{}).get("label","")),
                        "Title": title, "Text": body,
                        "Score": entry.get("im:rating",{}).get("label",""),
                        "Product_Tag": brand,
                        "URL": f"https://apps.apple.com/{cc}/app/id{app_id}"
                    })
                    added += 1
                    if len(rows) >= needed:
                        break

                logger.info(f"    [{cc.upper()}] p{page}: +{added} → {len(rows):,}/{needed:,}")
                time.sleep(0.8)
            except Exception as e:
                logger.warning(f"    App Store error [{cc}] p{page}: {e}")
                break
        time.sleep(0.5)

    return pd.DataFrame(rows)


# ─────────────────────────── Reddit ───────────────────────────────────────────

_AS_POSTS = "https://arctic-shift.photon-reddit.com/api/posts/search"
_RD_SESSION = requests.Session()
_RD_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0",
    "Accept": "application/json"
})

def scrape_reddit(brand, needed, seen_texts, seen_ids, date_restrict):
    logger.info(f"  [Reddit] {brand} — need {needed:,}")
    if needed <= 0:
        return pd.DataFrame()

    rows = []
    cutoff_dt  = datetime.datetime(2025, 12, 1, tzinfo=datetime.timezone.utc) if date_restrict \
                 else datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc)
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    cutoff_ts  = int(cutoff_dt.timestamp())

    keywords = REDDIT_KEYWORDS_MAP.get(brand, [brand.lower()])

    for sub in REDDIT_SUBREDDITS:
        if len(rows) >= needed:
            break
        for kw in keywords:
            if len(rows) >= needed:
                break
            params = {"subreddit": sub, "title": kw, "limit": 100,
                      "after": cutoff_iso, "sort": "desc"}
            try:
                resp = _RD_SESSION.get(_AS_POSTS, params=params, timeout=25)
                if resp.status_code != 200:
                    continue
                items = resp.json().get("data", []) or []
                for item in items:
                    pid   = item.get("id","")
                    ts    = int(item.get("created_utc", 0))
                    if date_restrict and ts < cutoff_ts:
                        continue
                    text  = clean_text(item.get("selftext","") or item.get("title",""))
                    if text in ("[deleted]","[removed]"):
                        text = clean_text(item.get("title",""))
                    if not text or text in seen_texts or pid in seen_ids:
                        continue

                    seen_ids.add(pid); seen_texts.add(text)
                    dt = datetime.datetime.utcfromtimestamp(ts)
                    rows.append({
                        "Review_ID": pid, "Platform": "Reddit",
                        "Source": f"r/{sub}", "Date": dt.strftime("%d/%m/%Y"),
                        "Username": str(item.get("author","")),
                        "Title": clean_text(item.get("title","")),
                        "Text": text, "Score": item.get("score",0),
                        "Product_Tag": brand,
                        "URL": f"https://www.reddit.com/r/{sub}/comments/{pid}/"
                    })
                    if len(rows) >= needed:
                        break

                logger.info(f"    r/{sub} '{kw}': {len(rows):,}/{needed:,}")
                time.sleep(1.2)
            except Exception as e:
                logger.warning(f"  Reddit error r/{sub} '{kw}': {e}")

    return pd.DataFrame(rows)


# ─────────────────────────── Main Orchestrator ────────────────────────────────

def orchestrate():
    for brand, info in BRANDS.items():
        logger.info(f"\n{'='*50}\nProcessing: {brand}\n{'='*50}")
        filepath = os.path.join("output", info["file"])
        if not os.path.exists(filepath):
            logger.error(f"Missing: {filepath}");  continue

        df = pd.read_excel(filepath, sheet_name="Raw Data")
        orig = len(df)

        # Normalise ID col
        if "Post_ID" in df.columns and "Review_ID" not in df.columns:
            df.rename(columns={"Post_ID":"Review_ID"}, inplace=True)

        # Date filter
        df["_dt"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
        if info["date_restrict"]:
            df = df[df["_dt"] >= CUTOFF_DATE]

        # Text dedup
        df["Text"] = df["Text"].fillna("").astype(str).str.strip()
        df.drop_duplicates(subset=["Text"], inplace=True)
        df.drop(columns=["_dt"], inplace=True)

        logger.info(f"After cleaning — orig:{orig} kept:{len(df)} shortfall:{info['target']-len(df)}")

        # Build shared seen sets from cleaned data
        seen_texts = set(df["Text"].tolist())
        seen_ids   = set(df["Review_ID"].astype(str).tolist())

        shortfall = info["target"] - len(df)

        if shortfall > 0:
            # Distribute: 40% Play, 40% App Store, 20% Reddit (approximate)
            play_need   = int(shortfall * 0.40)
            app_need    = int(shortfall * 0.40)
            reddit_need = shortfall - play_need - app_need  # remainder

            # ---- Play Store ----
            play_df = scrape_play(brand, info["play_id"], play_need,
                                  seen_texts, seen_ids, info["date_restrict"])
            df = pd.concat([df, play_df], ignore_index=True)
            logger.info(f"After Play Store: {len(df):,}")

            # Recalculate remaining shortfall
            remaining = info["target"] - len(df)
            app_need  = min(app_need + max(0, play_need - len(play_df)), remaining)

            # ---- App Store ----
            app_df = scrape_appstore(brand, info["app_id"], app_need,
                                     seen_texts, seen_ids, info["date_restrict"])
            df = pd.concat([df, app_df], ignore_index=True)
            logger.info(f"After App Store:  {len(df):,}")

            # Recalculate remaining shortfall
            remaining   = info["target"] - len(df)
            reddit_need = min(reddit_need + max(0, app_need - len(app_df)), remaining)

            # ---- Reddit ----
            if reddit_need > 0:
                rd_df = scrape_reddit(brand, reddit_need,
                                      seen_texts, seen_ids, info["date_restrict"])
                df = pd.concat([df, rd_df], ignore_index=True)
                logger.info(f"After Reddit:     {len(df):,}")

        # ── Final clean pass ──────────────────────────────────────────────────
        df["Text"] = df["Text"].astype(str).str.strip()
        df.drop_duplicates(subset=["Text"], inplace=True)  # absolute guarantee
        df = df.head(info["target"])

        # Keep only raw columns
        raw_cols = ["Review_ID","Platform","Source","Date","Username","Title","Text","Score","Product_Tag","URL"]
        df = df[[c for c in raw_cols if c in df.columns]]

        out = os.path.join("output", f"{brand.lower()}_data.xlsx")
        df.to_excel(out, index=False)
        dupes_left = df["Text"].duplicated().sum()
        logger.info(f"[{brand}] SAVED {len(df):,} rows | Text dupes remaining: {dupes_left} → {out}\n")

if __name__ == "__main__":
    orchestrate()
