# =============================================================================
#  trim_to_target.py  --  Trim/top-up each brand file to exact row targets
# =============================================================================
import os, sys, time, logging, datetime
import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("trim.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from config import COLUMNS
from utils.deduplicator import dedup_dataframe
from utils.exporter     import export_to_excel
from google_play_scraper import reviews as gp_reviews, Sort

OUTPUT_DIR = "output"

TARGETS = {
    "zomato_data.xlsx":   {"target": 25000, "app_id": "com.application.zomato",          "tag": "Zomato"},
    "blinkit_data.xlsx":  {"target": 20000, "app_id": "com.grofers.customerapp",          "tag": "Blinkit"},
    "district_data.xlsx": {"target": 10000, "app_id": "com.application.zomato.district",  "tag": "District"},
}


def scrape_topup(app_id: str, tag: str, needed: int) -> list:
    """Scrape extra Play Store reviews to fill shortfall."""
    rows  = []
    token = None
    fetch = int(needed * 1.4)   # over-fetch to cover dedup loss
    logger.info(f"  Fetching ~{fetch:,} extra {tag} reviews from Play Store...")

    while len(rows) < fetch:
        count = min(200, fetch - len(rows))
        try:
            result, token = gp_reviews(
                app_id, lang="en", country="in",
                sort=Sort.MOST_RELEVANT,
                count=count, continuation_token=token,
            )
        except Exception as e:
            logger.warning(f"  Error: {e}")
            break
        if not result:
            # Try different sort
            try:
                result, token = gp_reviews(
                    app_id, lang="en", country="us",
                    sort=Sort.NEWEST, count=count, continuation_token=None,
                )
            except Exception:
                break

        for r in result:
            d = r.get("at")
            date_str = d.strftime("%d/%m/%Y") if isinstance(d, datetime.datetime) else ""
            rows.append({
                "Post_ID":     str(r.get("reviewId", "")),
                "Platform":    "Google Play",
                "Source":      f"Play Store - {tag}",
                "Date":        date_str,
                "Username":    str(r.get("userName", "")),
                "Title":       str(r.get("title", "") or ""),
                "Text":        str(r.get("content", "") or ""),
                "Score":       r.get("score", ""),
                "Product_Tag": tag,
                "URL":         f"https://play.google.com/store/apps/details?id={app_id}",
            })
        if not token:
            break
        time.sleep(1.5)

    logger.info(f"  Fetched {len(rows):,} extra rows")
    return rows


def main():
    for fname, cfg in TARGETS.items():
        target  = cfg["target"]
        app_id  = cfg["app_id"]
        tag     = cfg["tag"]
        path    = os.path.join(OUTPUT_DIR, fname)

        # Load existing file
        df = pd.read_excel(path, sheet_name="Raw Data", dtype=str).fillna("")
        current = len(df)
        logger.info(f"\n{fname}: {current:,} / {target:,}")

        if current < target:
            shortfall = target - current
            logger.info(f"  Need {shortfall:,} more rows")

            # Scrape top-up
            extra_rows = scrape_topup(app_id, tag, shortfall)
            extra_df   = pd.DataFrame(extra_rows).reindex(columns=COLUMNS, fill_value="").fillna("")

            # Merge + dedup
            df = pd.concat([df, extra_df], ignore_index=True)
            df = dedup_dataframe(df)
            logger.info(f"  After merge+dedup: {len(df):,} rows")

        elif current > target:
            logger.info(f"  Trimming {current - target:,} rows")

        # Trim or pad to exact target
        if len(df) >= target:
            df = df.iloc[:target].copy()
        else:
            logger.warning(f"  Still {target - len(df):,} short after top-up — keeping all {len(df):,}")

        df = df.reindex(columns=COLUMNS, fill_value="").fillna("").reset_index(drop=True)

        logger.info(f"  Exporting {len(df):,} rows -> {fname}")
        export_to_excel(df, path)
        logger.info(f"  DONE: {fname} = {len(df):,} rows")

    logger.info("\n" + "=" * 50)
    logger.info("Final counts:")
    for fname in TARGETS:
        path = os.path.join(OUTPUT_DIR, fname)
        df   = pd.read_excel(path, sheet_name="Raw Data", dtype=str)
        logger.info(f"  {fname:<30} {len(df):>7,} rows")
    logger.info("[DONE]")


if __name__ == "__main__":
    main()
