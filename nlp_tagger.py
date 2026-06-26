import os
import sys
import logging
import pandas as pd
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# =============================================================================
# 1. Advanced Sentiment Analyzer Setup
# =============================================================================
custom_lexicon = {
    "fraud": -3.0, "scam": -3.0, "pathetic": -3.5, "worst": -3.5, "stale": -3.0,
    "expired": -3.0, "rotten": -3.0, "bug": -3.0, "missing": -2.0, "fake": -3.0,
    "cold": -1.5, "rude": -2.5, "late": -2.0, "delayed": -1.5,
    "fresh": 2.5, "fastest": 3.0, "polite": 2.5, "saver": 2.0, "amazing": 3.0,
    "love": 3.0, "best": 3.5, "quick": 2.0
}
analyzer = SentimentIntensityAnalyzer()
analyzer.lexicon.update(custom_lexicon)

def get_sentiment(text, score_val):
    if not isinstance(text, str) or text.strip() == "":
        return "Neutral", 0.0

    vs = analyzer.polarity_scores(text)
    compound = vs['compound']

    if compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    try:
        m = re.search(r"(\d+)", str(score_val))
        score = float(m.group(1)) if m else None
    except:
        score = None
    
    if score is not None:
        if score <= 2:
            sentiment = "Negative"
        elif score >= 4 and sentiment != "Negative":
            if compound > -0.2: 
                sentiment = "Positive"

    return sentiment, compound

# =============================================================================
# 2. Hybrid CX Engine: Universal L1 with Platform-Specific L2s
# =============================================================================
# This approach gives unified C-suite reporting at L1, but actionable 
# platform-specific insights at L2.

# Generic rules that apply to all brands
GENERIC_TAXONOMY = {
    "Ease of Use & Digital Experience": {
        "App/Website Navigation": [r"app crash", r"\bglitch\b", r"\bbuggy\b", r"hangs?", r"slow app", r"\bui\b", r"\binterface\b", r"\bupdate\b", r"stuck", r"loading", r"crashes", r"\berror\b", r"not working"],
        "Checkout & Payment Process": [r"\bpayment\b", r"transaction", r"\bwallet\b", r"\bupi\b", r"\bcard\b"]
    },
    "Value & Pricing": {
        "Price & Affordability": [r"\bexpensive\b", r"overpriced", r"\bcostly\b", r"cheaper", r"high price"],
        "Fees & Surcharges": [r"platform fee", r"handling fee", r"surge", r"hidden charge", r"tax", r"delivery charge", r"packing charge", r"packaging charge", r"cancellation charge", r"cancellation fee", r"extra charge"],
        "Promotions & Loyalty": [r"\bdiscount\b", r"\bcoupon\b", r"\bpromo\b", r"\boffer\b", r"fake discount", r"bachat"],
        "Competitor Comparisons": [r"\bswiggy\b", r"\bzepto\b", r"\binstamart\b", r"\bdunzo\b", r"\bbigbasket\b", r"book my show", r"bms", r"paytm insider", r"competitor"]
    },
    "Customer Support & Resolution": {
        "Refund & Policy Disputes": [r"\brefund\b", r"money back", r"return money", r"deducted", r"charged twice"],
        "Self-Service & Bot Effectiveness": [r"\bbot\b", r"automated", r"scripted", r"copy paste"],
        "Agent Helpfulness": [r"customer (?:service|care|support|executive)", r"\bchat\b", r"no response", r"unhelpful", r"worst support", r"no help", r"contacting them", r"no reply", r"didn't reply", r"not replying", r"resolved"]
    }
}

# Platform-specific rules injected under the Universal L1s
BRAND_SPECIFIC_TAXONOMY = {
    "Zomato": {
        "Product & Service Quality": {
            "Food Quality (Stale/Cold)": [r"\bstale\b", r"\bspoiled\b", r"\bsmell(?:s|y)?\b", r"\bcold food\b", r"tasteless", r"\bawful\b"],
            "Hygiene (Bugs/Hair)": [r"\bbug\b", r"\binsect\b", r"\bhygiene\b", r"\bdirty\b", r"\bfly\b", r"\bhair\b", r"cockroach", r"worm"],
            "Order Accuracy (Missing/Wrong)": [r"\bmissing\b", r"wrong item", r"incorrect order", r"\bforgot\b", r"half eaten", r"\bportion\b"],
            "Restaurant/Menu Availability": [r"chain of restaurants", r"accept an order", r"accept order", r"restaurant network"]
        },
        "Fulfillment & Logistics": {
            "Speed of Delivery": [r"\blate\b", r"\bdelay(?:ed)?\b", r"\bslow\b", r"took (?:so|too) long", r"\bfast(?:est)?\b", r"\bquick\b", r"on time", r"waiting"],
            "Staff Professionalism": [r"delivery (?:boy|guy|partner|executive|person|valet)", r"\brude\b", r"\bunprofessional\b", r"extra money", r"\bbehavior\b", r"\btheft\b"],
            "Item Condition & Packaging": [r"spill(?:ed)?", r"\bdamaged\b", r"poor packaging", r"\bleak(?:ing|age)?\b"],
            "Fleet/Job Issues (Riders)": [r"delivery job", r"gig worker", r"strike", r"onboarding"],
            "Gold Delivery Radius/Distance Cap": [r"(?=.*\bgold\b)(?=.*(?:distance|radius|7\s*km|limit))", r"free delivery limit", r"distance limit"]
        },
        "Customer Support & Resolution": {
            "Premium/Gold Support Failure": [r"(?=.*\bgold\b)(?=.*(?:support|bot|refund|executive|care))", r"(?=.*\bmembership\b)(?=.*(?:support|bot|refund|executive|care))"]
        },
        "Value & Pricing": {
            "Gold Hidden Fees/Platform Charges": [r"(?=.*\bgold\b)(?=.*(?:platform fee|handling fee|hidden charge|tax))", r"(?=.*\bmembership\b)(?=.*(?:platform fee|handling fee|hidden charge|tax))"]
        }
    },
    "Blinkit": {
        "Product & Service Quality": {
            "Grocery Expiry & Freshness": [r"\bexpir(?:ed|y)\b", r"out of date", r"past date", r"\brotten\b", r"\bfungus\b", r"\bmould\b"],
            "Counterfeit/Fake Brands": [r"\bfake\b", r"\bcounterfeit\b", r"\bduplicate\b", r"original"],
            "Order Accuracy (Missing/Wrong)": [r"\bmissing\b", r"wrong item", r"incorrect order", r"\bforgot\b"],
            "Product Assortment & Catalog": [r"single item", r"assortment", r"brand not available", r"more items", r"out of stock", r"not available", r"unavailable"]
        },
        "Fulfillment & Logistics": {
            "10-Min Delivery Promise": [r"10 (?:min|minute)s?", r"\blate\b", r"\bdelay(?:ed)?\b", r"\bfast(?:est)?\b", r"\bquick\b", r"on time"],
            "Staff Professionalism": [r"delivery (?:boy|guy|partner|executive|person)", r"\brude\b", r"\bunprofessional\b", r"extra money", r"\bbehavior\b"]
        },
        "Customer Support & Resolution": {
            "Return/Replacement Policy": [r"replace", r"return policy", r"images rejected", r"can't return", r"replacement"]
        },
        "Value & Pricing": {
            "Packaging Bag Issues": [r"carry bag", r"paper bag", r"bare hand", r"paid for bag"]
        }
    },
    "District": {
        "Ease of Use & Digital Experience": {
            "Location & City Availability": [r"my city", r"location", r"not available in", r"dindigul"]
        },
        "Events & Venues": {
            "Ticketing & Booking": [r"\bticket\b", r"\bbooking\b", r"sold out", r"cancel(?:led)? event", r"\bevent\b"],
            "Venue Experience (Crowd/Seating)": [r"\bvenue\b", r"\bcrowd\b", r"\bseating\b", r"ambience", r"\bvibe\b"],
            "Entry & Management": [r"\bentry\b", r"\bbouncer\b", r"\bmanagement\b", r"denied", r"not allowed"]
        },
        "Product & Service Quality": {
            "Restaurant Acceptance Issues": [r"reservation", r"refused", r"didn't accept", r"didn't honor"]
        },
        "Value & Pricing": {
            "District Pass & Subscriptions": [r"distric pass", r"district pass", r"subscription"]
        }
    }
}

# Compile dictionaries
def compile_taxonomy(tax_dict):
    compiled = {}
    for l1, l2_dict in tax_dict.items():
        compiled[l1] = {}
        for l2, patterns in l2_dict.items():
            compiled[l1][l2] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return compiled

C_GENERIC = compile_taxonomy(GENERIC_TAXONOMY)
C_BRANDS = {brand: compile_taxonomy(tax) for brand, tax in BRAND_SPECIFIC_TAXONOMY.items()}

def categorize(text, brand, title=""):
    combined = f"{title} {text}"
    if not combined.strip():
        return "", ""
        
    l1_matches = set()
    l2_matches = set()
    
    # 1. Apply Generic Rules
    for l1, l2_dict in C_GENERIC.items():
        for l2, regex_list in l2_dict.items():
            for r in regex_list:
                if r.search(combined):
                    l1_matches.add(l1)
                    l2_matches.add(l2)
                    break
                    
    # 2. Apply Brand-Specific Rules
    if brand in C_BRANDS:
        for l1, l2_dict in C_BRANDS[brand].items():
            for l2, regex_list in l2_dict.items():
                for r in regex_list:
                    if r.search(combined):
                        l1_matches.add(l1)
                        l2_matches.add(l2)
                        break
                        
    return ", ".join(sorted(l1_matches)), ", ".join(sorted(l2_matches))

# =============================================================================
# 3. Execution Engine
# =============================================================================
def process_file(filepath, brand_name):
    logger.info(f"Processing: {filepath} as {brand_name}")
    df = pd.read_excel(filepath, sheet_name=0)
    
    sentiments = []
    scores = []
    l1_cats = []
    l2_cats = []
    
    total = len(df)
    for idx, row in df.iterrows():
        text = str(row.get('Text', ''))
        title = str(row.get('Title', ''))
        score = row.get('Score', None)
        
        sentiment_label, compound_score = get_sentiment(text, score)
        sentiments.append(sentiment_label)
        scores.append(round(compound_score, 3))
        
        l1, l2 = categorize(text, brand_name, title)
        if not l1:
            l1 = "Uncategorized/General Feedback"
            l2 = "No Specific Issue Stated"
        
        l1_cats.append(l1)
        l2_cats.append(l2)
        
        if (idx + 1) % 5000 == 0:
            logger.info(f"  Processed {idx + 1}/{total} rows")
            
    df['Sentiment'] = sentiments
    df['Sentiment_Score'] = scores
    df['L1_Category'] = l1_cats
    df['L2_Specific_Issue'] = l2_cats
    
    out_path = filepath.replace(".xlsx", "_enriched.xlsx")
    
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Raw Data", index=False)
        
        sent_dist = df['Sentiment'].value_counts().reset_index()
        sent_dist.columns = ['Sentiment', 'Count']
        sent_dist.to_excel(writer, sheet_name="Summary", startrow=1, startcol=0, index=False)
        
        l1_dist = df['L1_Category'].value_counts().reset_index()
        l1_dist.columns = [f'{brand_name} L1 Category', 'Count']
        l1_dist.to_excel(writer, sheet_name="Summary", startrow=1, startcol=3, index=False)
        
        df_exploded = df.assign(L2_Specific_Issue=df['L2_Specific_Issue'].str.split(', ')).explode('L2_Specific_Issue')
        l2_dist = df_exploded['L2_Specific_Issue'].replace("", "None/Uncategorized").value_counts().reset_index()
        l2_dist.columns = [f'{brand_name} Specific Issue', 'Count']
        l2_dist.to_excel(writer, sheet_name="Summary", startrow=1, startcol=6, index=False)
        
        worksheet = writer.sheets["Summary"]
        worksheet.cell(row=1, column=1, value="Sentiment Breakdown")
        worksheet.cell(row=1, column=4, value="Primary Theme Breakdown")
        worksheet.cell(row=1, column=7, value="Specific Issue Breakdown")
        
    logger.info(f"Saved highly enriched file to: {out_path}")

if __name__ == "__main__":
    base_dir = "output"
    files = [
        ("zomato_data.xlsx", "Zomato"),
        ("blinkit_data.xlsx", "Blinkit"),
        ("district_data.xlsx", "District")
    ]
    
    for f, brand in files:
        full_path = os.path.join(base_dir, f)
        if os.path.exists(full_path):
            process_file(full_path, brand)
        else:
            logger.warning(f"File not found: {full_path}")
            
    logger.info("All NLP Tagging Complete.")
