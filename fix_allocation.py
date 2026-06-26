# =============================================================================
#  fix_allocation.py  --  Re-tag Play Store rows by app ID in URL, then export
# =============================================================================
"""
The tagger bug caused District + Blinkit Play Store rows to be mislabeled as
Zomato (because their reviews mention "Zomato"). The fix: re-assign Product_Tag
based on the URL's app package ID, which is authoritative.

App IDs:
  com.application.zomato         -> Zomato
  com.grofers.customerapp        -> Blinkit
  com.application.zomato.district -> District

Then re-export the 3 brand files.
"""
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
        logging.FileHandler("fix_allocation.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

from config import COLUMNS
from utils.tagger       import expand_rows_by_tag, get_product_tags
from utils.deduplicator import dedup_dataframe
from utils.exporter     import export_to_excel

OUTPUT_DIR = "output"

# URL fragment -> correct Product_Tag
APP_ID_TAGS = {
    "com.application.zomato.district": "District",
    "com.grofers.customerapp":          "Blinkit",
    "com.application.zomato":           "Zomato",   # must be last (substring match)
}

# App Store app IDs
AS_ID_TAGS = {
    "id=434613896":  "Zomato",
    "id6670536058":  "District",
    "id960335206":   "Blinkit",
    # URL format: /app/id434613896
    "/id434613896":  "Zomato",
    "/id6670536058": "District",
    "/id960335206":  "Blinkit",
}


def infer_tag_from_url(url: str, platform: str, existing_tag: str) -> str:
    """Return the correct Product_Tag based on URL app-ID, if determinable."""
    url_lower = url.lower()

    if platform == "Google Play":
        for app_id, tag in APP_ID_TAGS.items():
            if app_id in url_lower:
                return tag

    if platform == "Apple App Store":
        for fragment, tag in AS_ID_TAGS.items():
            if fragment in url_lower:
                return tag

    return existing_tag   # keep existing tag for Reddit/LinkedIn/etc.


# ---------------------------------------------------------------------------
# 1. Load all brand xlsx files (they contain everything)
# ---------------------------------------------------------------------------
logger.info("Loading all xlsx files...")
all_dfs = []
for fname in ["zomato_data.xlsx", "blinkit_data.xlsx", "district_data.xlsx"]:
    path = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(path):
        df = pd.read_excel(path, sheet_name="Raw Data", dtype=str).fillna("")
        all_dfs.append(df)
        logger.info(f"  {fname}: {len(df):,} rows")

# Load App Store JSON files (may have additional rows not in xlsx)
logger.info("Loading App Store JSON files...")
appstore_rows = []
for fname, brand in [
    ("appstore_zomato.json",   "Zomato"),
    ("appstore_blinkit.json",  "Blinkit"),
    ("appstore_district.json", "District"),
]:
    path = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for r in data:
            r["Product_Tag"] = brand   # authoritative
        appstore_rows.extend(data)
        logger.info(f"  {fname}: {len(data):,} rows")

as_df = pd.DataFrame(appstore_rows) if appstore_rows else pd.DataFrame()

# ---------------------------------------------------------------------------
# 2. Combine into one master DataFrame
# ---------------------------------------------------------------------------
master = pd.concat(all_dfs + ([as_df] if not as_df.empty else []), ignore_index=True)
for col in COLUMNS:
    if col not in master.columns:
        master[col] = ""
master = master.reindex(columns=COLUMNS, fill_value="").fillna("")

logger.info(f"Master before fix: {len(master):,} rows")

# ---------------------------------------------------------------------------
# 3. Re-assign Product_Tag using URL for Play Store / App Store rows
# ---------------------------------------------------------------------------
logger.info("Re-assigning Product_Tag from URL...")

fixed = []
tag_changes = {"Zomato->District": 0, "Zomato->Blinkit": 0, "other": 0}

for _, row in master.iterrows():
    url      = str(row.get("URL", ""))
    platform = str(row.get("Platform", ""))
    old_tag  = str(row.get("Product_Tag", ""))

    new_tag = infer_tag_from_url(url, platform, old_tag)

    if new_tag != old_tag:
        key = f"{old_tag}->{new_tag}"
        tag_changes[key] = tag_changes.get(key, 0) + 1
        row = row.copy()
        row["Product_Tag"] = new_tag

    fixed.append(dict(row))

logger.info(f"Tag corrections: {dict((k,v) for k,v in tag_changes.items() if v>0)}")

df = pd.DataFrame(fixed)
for col in COLUMNS:
    if col not in df.columns:
        df[col] = ""
df = df.reindex(columns=COLUMNS, fill_value="").fillna("")

# ---------------------------------------------------------------------------
# 4. Re-tag non-store rows (Reddit etc) using text keywords
# ---------------------------------------------------------------------------
logger.info("Re-tagging Reddit/social rows with fixed tagger...")
store_mask  = df["Platform"].isin(["Google Play", "Apple App Store"])
store_df    = df[store_mask].copy()
social_df   = df[~store_mask].copy()

social_rows = social_df.to_dict("records")
retagged    = expand_rows_by_tag(social_rows)
social_df2  = pd.DataFrame(retagged).reindex(columns=COLUMNS, fill_value="").fillna("")

df_final = pd.concat([store_df, social_df2], ignore_index=True)
df_final = dedup_dataframe(df_final)
df_final = df_final.reset_index(drop=True)

logger.info(f"Final after dedup: {len(df_final):,} rows")

# ---------------------------------------------------------------------------
# 5. Split by brand and export
# ---------------------------------------------------------------------------
brand_map = {
    "Zomato":      "zomato_data.xlsx",
    "Zomato Gold": "zomato_data.xlsx",
    "HyperPure":   "zomato_data.xlsx",
    "Blinkit":     "blinkit_data.xlsx",
    "District":    "district_data.xlsx",
}

grouped = {}
for _, row in df_final.iterrows():
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

# Full breakdown
logger.info("\nPlatform x Brand breakdown:")
pivot = df_final.groupby(["Platform", "Product_Tag"]).size().reset_index(name="Count")
for _, r in pivot.sort_values(["Platform","Count"], ascending=[True,False]).iterrows():
    logger.info(f"  {r['Platform']:<25} {r['Product_Tag']:<15} {r['Count']:>7,}")

logger.info("\n[DONE] Allocation fixed and files exported.")
