# =============================================================================
#  utils/deduplicator.py  —  Hash-based deduplication
# =============================================================================
import hashlib
import pandas as pd
from typing import List


def _row_hash(row: pd.Series) -> str:
    """SHA-256 hash of the key identity fields of a row."""
    key = "|".join([
        str(row.get("Platform", "")),
        str(row.get("Source", "")),
        str(row.get("Post_ID", "")),
        str(row.get("Text", ""))[:500],   # first 500 chars of text is enough
    ])
    return hashlib.sha256(key.encode("utf-8", errors="replace")).hexdigest()


def dedup_rows(rows: List[dict]) -> List[dict]:
    """Deduplicate a list of row-dicts in-memory (before DataFrame conversion)."""
    seen = set()
    unique = []
    for row in rows:
        key = "|".join([
            str(row.get("Platform", "")),
            str(row.get("Source", "")),
            str(row.get("Post_ID", "")),
            str(row.get("Text", ""))[:500],
        ])
        h = hashlib.sha256(key.encode("utf-8", errors="replace")).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(row)
    return unique


def dedup_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate a DataFrame, preserving first occurrence."""
    df = df.copy()
    df["_hash"] = df.apply(_row_hash, axis=1)
    df = df.drop_duplicates(subset=["_hash"], keep="first")
    df = df.drop(columns=["_hash"])
    df = df.reset_index(drop=True)
    return df
