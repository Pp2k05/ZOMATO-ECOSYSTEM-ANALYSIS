# =============================================================================
#  topup.py  --  Top up existing data to hit 50,000 row target
#  Loads existing checkpoints, pulls missing rows, re-exports 3 brand files
# =============================================================================
import os, sys, time, logging
import pandas as pd

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("topup_run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from config import COLUMNS
from google_play_scraper import reviews as gp_reviews, Sort
from utils.tagger       import expand_rows_by_tag
from utils.deduplicator import dedup_rows, dedup_dataframe
from utils.exporter     import export_to_excel

GRAND_TARGET = 50_000

TOPUP_APPS = {
    # Need many more Zomato reviews (different sort = different reviews)
    "Zomato_helpful": {
        "app_id": "com.application.zomato",
        "target": 12000,
        "product_tag": "Zomato",
        "sort": Sort.MOST_RELEVANT,
    },
    "Blinkit_helpful": {
        "app_id": "com.grofers.customerapp",
        "target": 10000,
        "product_tag": "Blinkit",
        "sort": Sort.MOST_RELEVANT,
    },
    # District with CORRECT app ID
    "District": {
        "app_id": "com.application.zomato.district",
        "target": 8000,
        "product_tag": "District",
        "sort": Sort.NEWEST,
    },
    "District_relevant": {
        "app_id": "com.application.zomato.district",
        "target": 5000,
        "product_tag": "District",
        "sort": Sort.MOST_RELEVANT,
    },
    # Extra Zomato from different countries
    "Zomato_newest2": {
        "app_id": "com.application.zomato",
        "target": 8000,
        "product_tag": "Zomato",
        "sort": Sort.NEWEST,
        "country": "us",
    },
    "Blinkit_newest2": {
        "app_id": "com.grofers.customerapp",
        "target": 6000,
        "product_tag": "Blinkit",
        "sort": Sort.NEWEST,
        "country": "us",
    },
}


def scrape_app(cfg: dict, label: str) -> list:
    rows   = []
    token  = None
    target = cfg["target"]
    country = cfg.get("country", "in")

    logger.info(f"  Scraping {label} ({cfg['app_id']}) target={target:,} country={country}")

    while len(rows) < target:
        need = min(200, target - len(rows))
        try:
            result, token = gp_reviews(
                cfg["app_id"],
                lang="en",
                country=country,
                sort=cfg["sort"],
                count=need,
                continuation_token=token,
            )
        except Exception as e:
            logger.warning(f"    Error: {e}")
            time.sleep(10)
            break

        if not result:
            break

        import datetime
        for r in result:
            date_obj = r.get("at")
            date_str = date_obj.strftime("%d/%m/%Y") if isinstance(date_obj, datetime.datetime) else ""
            rows.append({
                "Post_ID":     str(r.get("reviewId", "")),
                "Platform":    "Google Play",
                "Source":      f"Play Store -- {label.split('_')[0]}",
                "Date":        date_str,
                "Username":    str(r.get("userName", "")),
                "Title":       str(r.get("title", "") or ""),
                "Text":        str(r.get("content", "") or ""),
                "Score":       r.get("score", ""),
                "Product_Tag": cfg["product_tag"],
                "URL":         f"https://play.google.com/store/apps/details?id={cfg['app_id']}",
            })

        if len(rows) % 1000 < 200:
            logger.info(f"    {label}: {len(rows):,}/{target:,}")

        if not token:
            break
        time.sleep(1.5)

    logger.info(f"    {label}: done -- {len(rows):,} rows")
    return rows[:target]


def main():
    logger.info("[TOPUP] Loading existing checkpoint data...")

    # Load all existing checkpoints
    existing_rows = []
    for fname in ["checkpoint_reddit.csv", "checkpoint_gplay.csv"]:
        path = f"output/{fname}"
        if os.path.exists(path) and os.path.getsize(path) > 100:
            df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
            existing_rows.extend(df.to_dict("records"))
            logger.info(f"  Loaded {len(df):,} rows from {fname}")

    logger.info(f"  Existing rows: {len(existing_rows):,}")

    # Scrape top-up data
    new_rows = []
    for label, cfg in TOPUP_APPS.items():
        logger.info(f"\nScraping top-up: {label}")
        rows = scrape_app(cfg, label)
        new_rows.extend(rows)
        logger.info(f"  Top-up total so far: {len(new_rows):,}")

    logger.info(f"\nAll top-up scraped: {len(new_rows):,} new rows")

    # Combine + deduplicate
    all_rows = existing_rows + new_rows
    logger.info(f"Combined: {len(all_rows):,}")

    expanded = expand_rows_by_tag(all_rows)
    logger.info(f"After expansion: {len(expanded):,}")

    unique   = dedup_rows(expanded)
    logger.info(f"After dedup: {len(unique):,}")

    # Build DataFrame
    df = pd.DataFrame(unique)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[[c for c in COLUMNS if c in df.columns or True]]
    df = df.reindex(columns=COLUMNS, fill_value="")
    df = dedup_dataframe(df)
    df = df.fillna("").reset_index(drop=True)

    logger.info(f"Final rows: {len(df):,}")

    # Split by brand and export
    brand_map = {
        "Zomato":    "zomato_data.xlsx",
        "Zomato Gold": "zomato_data.xlsx",
        "HyperPure": "zomato_data.xlsx",
        "Blinkit":   "blinkit_data.xlsx",
        "District":  "district_data.xlsx",
    }

    os.makedirs("output", exist_ok=True)
    grouped = {}
    for _, row in df.iterrows():
        tag   = str(row.get("Product_Tag", "Zomato"))
        fname = brand_map.get(tag, "zomato_data.xlsx")
        grouped.setdefault(fname, []).append(row.to_dict())

    logger.info("\n" + "=" * 60)
    total = 0
    for fname, brand_rows in grouped.items():
        bdf = pd.DataFrame(brand_rows).reindex(columns=COLUMNS, fill_value="").fillna("")
        out = f"output/{fname}"
        export_to_excel(bdf, out)
        logger.info(f"  {fname:<30}  {len(bdf):>7,} rows")
        total += len(bdf)

    logger.info(f"\nGRAND TOTAL: {total:,} rows")
    if total >= GRAND_TARGET:
        logger.info(f"[OK] Target of {GRAND_TARGET:,} met!")
    else:
        logger.warning(f"[WARN] Still {GRAND_TARGET - total:,} short")
    logger.info("[DONE]")


if __name__ == "__main__":
    main()
