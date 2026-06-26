# =============================================================================
#  utils/tagger.py  --  Assign Product_Tag(s) to a piece of text
# =============================================================================
from typing import List
from config import KEYWORD_PRODUCT_MAP

# Platforms where the scraper already knows the exact brand --
# do NOT override with keyword matching (a Blinkit review saying
# "owned by Zomato" should stay tagged Blinkit, not be moved to Zomato).
_TRUSTED_PLATFORMS = {"Google Play", "Apple App Store"}


def get_product_tags(text: str, title: str = "") -> List[str]:
    """
    Return a deduplicated list of Product_Tag values found in *text* or *title*.
    Longer / more-specific phrases in KEYWORD_PRODUCT_MAP are checked first.
    Returns ['Zomato'] as default if nothing matches.
    """
    combined = (f"{title} {text}").lower()
    tags: List[str] = []

    for keyword, product in KEYWORD_PRODUCT_MAP:
        if keyword in combined and product not in tags:
            tags.append(product)

    return tags if tags else ["Zomato"]


def expand_rows_by_tag(rows: List[dict]) -> List[dict]:
    """
    For each row:
      - If the Platform is a trusted source (Play Store / App Store), keep the
        scraper-assigned Product_Tag unchanged.  The scraper knows the brand
        definitively; keyword matching would corrupt it (e.g. a Blinkit review
        mentioning 'Zomato' would incorrectly end up in zomato_data.xlsx).
      - Otherwise (Reddit, Twitter, Quora, News, LinkedIn) infer brand from
        text keywords and duplicate the row once per matched brand.
    """
    expanded: List[dict] = []

    for row in rows:
        platform     = str(row.get("Platform", ""))
        existing_tag = str(row.get("Product_Tag", "")).strip()

        # --- Trusted source: keep scraper-assigned tag as-is ---
        if platform in _TRUSTED_PLATFORMS and existing_tag:
            expanded.append(row)
            continue

        # --- Other sources: infer brand from text ---
        tags = get_product_tags(
            str(row.get("Text",  "")),
            str(row.get("Title", ""))
        )

        if len(tags) == 1:
            row["Product_Tag"] = tags[0]
            expanded.append(row)
        else:
            # Multi-brand post: one row per brand
            for tag in tags:
                new_row = dict(row)
                new_row["Product_Tag"] = tag
                new_row["Post_ID"]     = f"{row.get('Post_ID', '')}_{tag[:3].upper()}"
                expanded.append(new_row)

    return expanded
