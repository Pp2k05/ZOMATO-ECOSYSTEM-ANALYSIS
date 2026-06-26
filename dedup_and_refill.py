import os
import sys
import json
import subprocess
import pandas as pd
from google_play_scraper import reviews as gp_reviews, Sort

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

TARGETS = {
    "Zomato": {"file": "zomato_data_enriched.xlsx", "target": 25000, "play_id": "com.application.zomato", "app_id": "434613896"},
    "Blinkit": {"file": "blinkit_data_enriched.xlsx", "target": 20000, "play_id": "com.grofers.customerapp", "app_id": "960335206"},
    "District": {"file": "district_data_enriched.xlsx", "target": 10000, "play_id": "com.application.zomato.district", "app_id": "6670536058"}
}

def scrape_play_store(app_id, brand, needed, existing_ids):
    print(f"\n--- Play Store Refill: {brand} (Target: {needed}) ---")
    if needed <= 0: return pd.DataFrame()
    
    rows = []
    seen = set(existing_ids)
    token = None
    
    # Use NEWEST to get fresh reviews not previously grabbed by MOST_RELEVANT
    # Iterate with token to get deep
    while len(rows) < needed:
        count = min(200, needed - len(rows) + 50) # Fetch slightly more
        try:
            res, token = gp_reviews(
                app_id, lang="en", country="in",
                sort=Sort.NEWEST, count=count, continuation_token=token
            )
            if not res: break
            
            added = 0
            for r in res:
                rid = str(r.get('reviewId', ''))
                if rid not in seen:
                    seen.add(rid)
                    dt = r.get('at')
                    date_str = dt.strftime('%d/%m/%Y') if dt else ''
                    rows.append({
                        'Review_ID': rid,
                        'Platform': 'Google Play Store',
                        'Source': 'Play Store',
                        'Date': date_str,
                        'Username': r.get('userName', ''),
                        'Title': 'Play Store Review',
                        'Text': r.get('content', ''),
                        'Score': r.get('score', ''),
                        'Product_Tag': brand,
                        'URL': f"https://play.google.com/store/apps/details?id={app_id}&reviewId={rid}"
                    })
                    added += 1
                    if len(rows) >= needed: break
            print(f"  Play Store: +{added} (Total: {len(rows)}/{needed})")
            if not token: break
        except Exception as e:
            print(f"  Play Store Error: {e}")
            break
            
    return pd.DataFrame(rows)

def orchestrate():
    node_targets = []
    
    # 1. Load and Dedup
    print("=== Phase 1: Deduplication ===")
    unique_dfs = {}
    for brand, info in TARGETS.items():
        filepath = os.path.join("output", info["file"])
        if not os.path.exists(filepath):
            print(f"File missing: {filepath}")
            continue
            
        df = pd.read_excel(filepath, sheet_name="Raw Data")
        
        # Standardize ID column
        if 'Post_ID' in df.columns and 'Review_ID' not in df.columns:
            df.rename(columns={'Post_ID': 'Review_ID'}, inplace=True)
            
        initial_len = len(df)
        df.drop_duplicates(subset=['Review_ID'], inplace=True)
        unique_len = len(df)
        
        shortfall = info["target"] - unique_len
        app_store_target = max(0, shortfall // 2)
        
        print(f"{brand} | Original: {initial_len} | Unique: {unique_len} | Shortfall: {shortfall}")
        
        unique_dfs[brand] = {
            "df": df,
            "shortfall": shortfall,
            "app_store_target": app_store_target,
            "existing_ids": df['Review_ID'].astype(str).tolist()
        }
        
        node_targets.append({
            "name": brand,
            "id": info["app_id"],
            "target": app_store_target,
            "existing_ids": unique_dfs[brand]["existing_ids"]
        })
        
    # 2. Write Node targets
    with open("refill_targets.json", "w", encoding="utf-8") as f:
        json.dump(node_targets, f)
        
    # 3. Execute App Store Scraper
    print("\n=== Phase 2: App Store Refill ===")
    subprocess.run(["node", "dynamic_appstore.js"], check=True)
    
    # 4. Process App Store data and run Play Store Refill
    print("\n=== Phase 3: Play Store Refill & Merge ===")
    for brand, info in TARGETS.items():
        udf = unique_dfs[brand]
        shortfall = udf["shortfall"]
        if shortfall <= 0:
            final_df = udf["df"].head(info["target"])
            final_df.to_excel(os.path.join("output", f"{brand.lower()}_data.xlsx"), index=False)
            continue
            
        # Load App Store data
        app_path = f"output/appstore_refill_{brand.lower()}.json"
        app_df = pd.DataFrame()
        if os.path.exists(app_path):
            try:
                with open(app_path, "r", encoding="utf-8") as f:
                    app_data = json.load(f)
                    if app_data:
                        app_df = pd.DataFrame(app_data)
                        print(f"{brand} App Store scraped: {len(app_df)}")
                        udf["existing_ids"].extend(app_df['Review_ID'].astype(str).tolist())
            except Exception as e:
                print(f"Error reading app store json: {e}")
                
        # Calculate remaining shortfall
        remaining_shortfall = shortfall - len(app_df)
        print(f"{brand} remaining shortfall for Play Store: {remaining_shortfall}")
        
        # Scrape Play Store
        play_df = scrape_play_store(info["play_id"], brand, remaining_shortfall, udf["existing_ids"])
        
        # Merge All
        final_df = pd.concat([udf["df"], app_df, play_df], ignore_index=True)
        
        # Drop duplicates one last time just to be absolutely certain
        final_df.drop_duplicates(subset=['Review_ID'], inplace=True)
        
        # Enforce exact target
        final_df = final_df.head(info["target"])
        
        # Drop the extra NLP columns so they are clean raw files
        raw_cols = ['Review_ID', 'Platform', 'Source', 'Date', 'Username', 'Title', 'Text', 'Score', 'Product_Tag', 'URL']
        for col in final_df.columns:
            if col not in raw_cols:
                final_df.drop(columns=[col], inplace=True)
        
        out_path = os.path.join("output", f"{brand.lower()}_data.xlsx")
        final_df.to_excel(out_path, index=False)
        print(f"[{brand}] FINAL SAVED -> {len(final_df)} unique rows to {out_path}\n")

if __name__ == "__main__":
    orchestrate()
