# =============================================================================
#  reexport.py  --  Reprocess all checkpoint data with fixed tagger & re-export
# =============================================================================
import os, sys, json, logging
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
        logging.FileHandler("reexport.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from config import COLUMNS
from utils.tagger       import expand_rows_by_tag
from utils.deduplicator import dedup_rows, dedup_dataframe
from utils.exporter     import export_to_excel

OUTPUT_DIR = "output"

# ---------------------------------------------------------------------------
# 1. Load ALL checkpoint CSVs
# ---------------------------------------------------------------------------
logger.info("Loading checkpoint CSV files...")
all_rows = []

checkpoints = [
    "checkpoint_reddit.csv",
    "checkpoint_gplay.csv",
    "checkpoint_appstore.csv",
    "checkpoint_twitter.csv",
]
for fname in checkpoints:
    path = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(path) and os.path.getsize(path) > 10:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
        all_rows.extend(df.to_dict("records"))
        logger.info(f"  {fname}: {len(df):,} rows")

# ---------------------------------------------------------------------------
# 2. Load topup Play Store data from topup log rows (re-scrape not needed --
#    load the per-app JSON files the scrapers already produced)
# ---------------------------------------------------------------------------
logger.info("Loading topup Play Store checkpoint (checkpoint_gplay.csv covers initial)...")
# The topup data was already exported into the xlsx files.
# Reload those xlsx files as the authoritative source.
brand_files = {
    "zomato_data.xlsx":   "Zomato",
    "blinkit_data.xlsx":  "Blinkit",
    "district_data.xlsx": "District",
}
xlsx_rows = []
for fname, brand in brand_files.items():
    path = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(path):
        df = pd.read_excel(path, sheet_name="Raw Data", dtype=str).fillna("")
        # Restore scraper-assigned Product_Tag from the file name brand
        # (but only for Play Store / App Store rows so tagger respects them)
        xlsx_rows.extend(df.to_dict("records"))
        logger.info(f"  {fname}: {len(df):,} rows loaded")

# ---------------------------------------------------------------------------
# 3. Load App Store JSON files
# ---------------------------------------------------------------------------
logger.info("Loading App Store JSON files...")
appstore_files = [
    ("appstore_zomato.json",   "Zomato"),
    ("appstore_blinkit.json",  "Blinkit"),
    ("appstore_district.json", "District"),
]
appstore_rows = []
for fname, brand in appstore_files:
    path = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Ensure Product_Tag is set correctly from source
        for r in data:
            r["Product_Tag"] = brand
        appstore_rows.extend(data)
        logger.info(f"  {fname}: {len(data):,} rows")

# ---------------------------------------------------------------------------
# 4. Combine: xlsx rows (already tagged) + appstore rows
#    The xlsx rows already have correct Product_Tags from the topup.
#    BUT they were tagged with the buggy tagger, so we need to re-tag
#    only the Reddit rows; Play Store rows should keep their xlsx tag.
# ---------------------------------------------------------------------------
logger.info("Combining all sources...")

# Separate Play Store / App Store rows (trusted tags) from Reddit (re-tag)
trusted_rows  = []
retag_rows    = []

for row in xlsx_rows:
    plat = str(row.get("Platform", ""))
    if plat in ("Google Play", "Apple App Store"):
        trusted_rows.append(row)
    else:
        retag_rows.append(row)

# Appstore rows are all trusted
trusted_rows.extend(appstore_rows)

logger.info(f"  Trusted (keep tag): {len(trusted_rows):,}")
logger.info(f"  To re-tag (Reddit/etc): {len(retag_rows):,}")

# Re-tag Reddit/social rows with fixed tagger
retagged = expand_rows_by_tag(retag_rows)
logger.info(f"  After re-tag expansion: {len(retagged):,}")

all_combined = trusted_rows + retagged
logger.info(f"  Combined total: {len(all_combined):,}")

# ---------------------------------------------------------------------------
# 5. Build DataFrame, dedup, split by brand, export
# ---------------------------------------------------------------------------
df = pd.DataFrame(all_combined)
for col in COLUMNS:
    if col not in df.columns:
        df[col] = ""
df = df.reindex(columns=COLUMNS, fill_value="").fillna("")
df = dedup_dataframe(df)
df = df.reset_index(drop=True)

logger.info(f"After dedup: {len(df):,} rows")

# Brand split
brand_map = {
    "Zomato":      "zomato_data.xlsx",
    "Zomato Gold": "zomato_data.xlsx",
    "HyperPure":   "zomato_data.xlsx",
    "Blinkit":     "blinkit_data.xlsx",
    "District":    "district_data.xlsx",
}

grouped = {}
for _, row in df.iterrows():
    tag   = str(row.get("Product_Tag", "Zomato"))
    fname = brand_map.get(tag, "zomato_data.xlsx")
    grouped.setdefault(fname, []).append(row.to_dict())

logger.info("\n" + "=" * 60)
total = 0
for fname, brand_rows in grouped.items():
    bdf = pd.DataFrame(brand_rows).reindex(columns=COLUMNS, fill_value="").fillna("")
    out = os.path.join(OUTPUT_DIR, fname)
    export_to_excel(bdf, out)
    logger.info(f"  {fname:<30}  {len(bdf):>7,} rows")
    total += len(bdf)

logger.info(f"\nGRAND TOTAL: {total:,} rows")

# Per-platform breakdown per brand
logger.info("\nPlatform x Brand breakdown:")
pivot = df.groupby(["Platform", "Product_Tag"]).size().reset_index(name="Count")
for _, r in pivot.iterrows():
    logger.info(f"  {r['Platform']:<25} {r['Product_Tag']:<12} {r['Count']:>7,}")

logger.info("\n[DONE] Files re-exported with corrected brand allocation.")
