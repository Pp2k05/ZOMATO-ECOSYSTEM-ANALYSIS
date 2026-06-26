# =============================================================================
#  main.py  --  Orchestrator: scrape -> merge -> dedup -> 3 brand Excel files
# =============================================================================
"""
Outputs:
  output/zomato_data.xlsx   -- all Zomato-brand data
  output/blinkit_data.xlsx  -- all Blinkit-brand data
  output/district_data.xlsx -- all District-brand data

Each file: Sheet 1 = Raw Data, Sheet 2 = Summary
"""

import os
import sys
import time
import logging
import pandas as pd

# Force UTF-8 stdout on Windows to avoid emoji UnicodeEncodeError
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from config import COLUMNS

from scrapers.reddit_scraper   import scrape_reddit
from scrapers.gplay_scraper    import scrape_google_play
from scrapers.appstore_scraper import scrape_app_store
from scrapers.twitter_scraper  import scrape_twitter
from scrapers.quora_scraper    import scrape_quora
from scrapers.news_scraper     import scrape_news

from utils.tagger       import expand_rows_by_tag
from utils.deduplicator import dedup_rows, dedup_dataframe
from utils.exporter     import export_to_excel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE = "scraper_run.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# Per-brand row targets (split of 50,000 grand total)
# ---------------------------------------------------------------------------
BRAND_TARGETS = {
    "Zomato":   25000,   # includes Zomato Gold
    "Blinkit":  15000,
    "District":  8000,
    "HyperPure": 2000,   # rolled into Zomato file
}

# Source-level targets (total across all brands)
SOURCE_TARGETS = {
    "Reddit":          17000,
    "Google Play":     20000,
    "Apple App Store": 13500,
    "Twitter":          5000,
    "Quora":            3500,
    "News":             2000,
}

# Brand → output file name
BRAND_FILES = {
    "Zomato":    "output/zomato_data.xlsx",
    "Zomato Gold": "output/zomato_data.xlsx",   # goes into Zomato file
    "HyperPure": "output/zomato_data.xlsx",      # goes into Zomato file
    "Blinkit":   "output/blinkit_data.xlsx",
    "District":  "output/district_data.xlsx",
}

GRAND_TARGET = 50_000


# ---------------------------------------------------------------------------
# Runner helper
# ---------------------------------------------------------------------------
def run_scraper(name: str, fn, target: int) -> list:
    logger.info("=" * 70)
    logger.info(f"  START: {name}  (target: {target:,})")
    logger.info("=" * 70)
    t0 = time.time()
    try:
        rows = fn(target)
    except Exception as e:
        logger.error(f"[{name}] FATAL: {e}", exc_info=True)
        rows = []
    logger.info(f"  {name}: {len(rows):,} rows in {time.time() - t0:.0f}s")
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("[START] Zomato Brand Scraping Pipeline")

    all_rows: list = []

    # ── 1. Reddit ──────────────────────────────────────────────────────────
    rows = run_scraper("Reddit", scrape_reddit, SOURCE_TARGETS["Reddit"])
    all_rows.extend(rows)
    _checkpoint(rows, "checkpoint_reddit.csv")

    # ── 2. Google Play ─────────────────────────────────────────────────────
    rows = run_scraper("Google Play", scrape_google_play, SOURCE_TARGETS["Google Play"])
    all_rows.extend(rows)
    _checkpoint(rows, "checkpoint_gplay.csv")

    # ── 3. Apple App Store ─────────────────────────────────────────────────
    rows = run_scraper("Apple App Store", scrape_app_store, SOURCE_TARGETS["Apple App Store"])
    all_rows.extend(rows)
    _checkpoint(rows, "checkpoint_appstore.csv")

    # ── 4. Twitter ─────────────────────────────────────────────────────────
    rows = run_scraper("Twitter", scrape_twitter, SOURCE_TARGETS["Twitter"])
    all_rows.extend(rows)
    _checkpoint(rows, "checkpoint_twitter.csv")

    # ── 5. Quora ───────────────────────────────────────────────────────────
    rows = run_scraper("Quora", scrape_quora, SOURCE_TARGETS["Quora"])
    all_rows.extend(rows)

    # ── 6. News Comments ───────────────────────────────────────────────────
    rows = run_scraper("News", scrape_news, SOURCE_TARGETS["News"])
    all_rows.extend(rows)

    logger.info(f"Raw rows collected: {len(all_rows):,}")

    # Expand multi-brand rows -- one row per brand mention
    logger.info("Expanding multi-brand rows...")
    expanded = expand_rows_by_tag(all_rows)
    logger.info(f"    After expansion: {len(expanded):,}")

    # Dedup
    logger.info("Deduplicating...")
    unique_rows = dedup_rows(expanded)
    logger.info(f"After dedup: {len(unique_rows):,}")

    # Build master DataFrame
    logger.info("Building DataFrame...")
    df = pd.DataFrame(unique_rows)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    # Drop internal helper columns
    df = df[[c for c in COLUMNS]]
    df = dedup_dataframe(df)
    df = df.fillna("").reset_index(drop=True)

    # Top-up if below grand target
    if len(df) < GRAND_TARGET:
        shortfall = GRAND_TARGET - len(df)
        logger.info(f"Shortfall: {shortfall:,} rows -- topping up via Google Play...")
        extra = run_scraper("Google Play (top-up)", scrape_google_play, int(shortfall * 1.4))
        extra = expand_rows_by_tag(extra)
        extra = dedup_rows(extra)
        df_extra = pd.DataFrame(extra)
        for col in COLUMNS:
            if col not in df_extra.columns:
                df_extra[col] = ""
        df_extra = df_extra[COLUMNS].fillna("")
        df = pd.concat([df, df_extra], ignore_index=True)
        df = dedup_dataframe(df)
        logger.info(f"After top-up: {len(df):,}")

    # Split by brand
    logger.info(f"Final row count: {len(df):,}")

    # Normalise Product_Tag: HyperPure + Zomato Gold → treated as Zomato family
    brand_map = {
        "Zomato":      "zomato_data.xlsx",
        "Zomato Gold": "zomato_data.xlsx",
        "HyperPure":   "zomato_data.xlsx",
        "Blinkit":     "blinkit_data.xlsx",
        "District":    "district_data.xlsx",
    }

    os.makedirs("output", exist_ok=True)

    # Group and export
    grouped: dict = {}
    for _, row in df.iterrows():
        tag   = str(row.get("Product_Tag", "Zomato"))
        fname = brand_map.get(tag, "zomato_data.xlsx")
        grouped.setdefault(fname, []).append(row.to_dict())

    file_row_counts = {}
    for fname, brand_rows in grouped.items():
        brand_df = pd.DataFrame(brand_rows)
        for col in COLUMNS:
            if col not in brand_df.columns:
                brand_df[col] = ""
        brand_df = brand_df[COLUMNS].fillna("").reset_index(drop=True)
        out_path = f"output/{fname}"
        export_to_excel(brand_df, out_path)
        file_row_counts[fname] = len(brand_df)

    # Final summary
    logger.info("=" * 70)
    logger.info("OUTPUT FILES")
    logger.info("=" * 70)
    for fname, count in file_row_counts.items():
        logger.info(f"  {fname:<30}  {count:>7,} rows")

    total = sum(file_row_counts.values())
    logger.info(f"GRAND TOTAL: {total:,} rows")

    if total >= GRAND_TARGET:
        logger.info(f"[OK] Target of {GRAND_TARGET:,} rows met!")
    else:
        logger.warning(f"[WARN] {GRAND_TARGET - total:,} rows below target")

    logger.info("Platform breakdown:")
    for plat, cnt in df.groupby("Platform").size().items():
        logger.info(f"  {plat:<22} {cnt:>7,}")

    logger.info(f"[DONE] Files saved in: {os.path.abspath('output')}")


# ---------------------------------------------------------------------------
def _checkpoint(rows: list, filename: str):
    try:
        os.makedirs("output", exist_ok=True)
        pd.DataFrame(rows).to_csv(
            f"output/{filename}", index=False, encoding="utf-8-sig"
        )
        logger.info(f"  💾  Checkpoint: output/{filename}  ({len(rows):,} rows)")
    except Exception as e:
        logger.warning(f"  Checkpoint save failed: {e}")


if __name__ == "__main__":
    main()
