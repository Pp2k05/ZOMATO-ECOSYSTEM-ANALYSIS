# =============================================================================
#  config.py  —  Central configuration for Zomato Data Scraping Project
# =============================================================================

# ---------------------------------------------------------------------------
# Keywords (used for Reddit, Twitter, Quora, News filtering)
# ---------------------------------------------------------------------------
KEYWORDS = [
    "Zomato", "Blinkit", "HyperPure", "Hyper Pure",
    "District app", "District by Zomato", "Zomato Gold",
    "Zomato Pro", "Zomato membership", "Grofers",
    "Zomato partner", "Zomato refund", "Zomato support",
    "Zomato restaurant",
]

# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------
SUBREDDITS = [
    "india", "bangalore", "hyderabad", "mumbai", "delhi",
    "pune", "chennai", "kolkata", "ahmedabad", "IndianFood",
    "AskIndia", "IndianStartups", "IndianBusiness",
    "IndiaInvestments", "FoodIndia",
]

REDDIT_MONTHS_BACK = 24        # Only include posts from last N months
REDDIT_COMMENTS_PER_POST = 20  # Top N comments per post

# ---------------------------------------------------------------------------
# Google Play Store
# ---------------------------------------------------------------------------
PLAY_STORE_APPS = {
    "Zomato": {
        "app_id": "com.application.zomato",
        "target": 8500,
        "product_tag": "Zomato",
    },
    "Blinkit": {
        "app_id": "com.grofers.customerapp",
        "target": 6500,
        "product_tag": "Blinkit",
    },
    "District": {
        "app_id": "com.application.zomato.district",
        "target": 4500,
        "product_tag": "District",
    },
}

# ---------------------------------------------------------------------------
# Apple App Store
# ---------------------------------------------------------------------------
APP_STORE_APPS = {
    "Zomato": {
        "app_name": "zomato-food-delivery",
        "app_id":   "884314303",
        "target":   5500,
        "product_tag": "Zomato",
    },
    "Blinkit": {
        "app_name": "blinkit-grocery-in-minutes",
        "app_id":   "1437814421",
        "target":   4500,
        "product_tag": "Blinkit",
    },
    "District": {
        "app_name": "district-events-things-to-do",
        "app_id":   "6450425020",
        "target":   3500,
        "product_tag": "District",
    },
}

# Countries to iterate over to bypass per-country caps
APP_STORE_COUNTRIES = ["in", "us", "gb", "au", "ca", "sg", "ae", "nz"]

# ---------------------------------------------------------------------------
# Twitter / X  (unofficial snscrape)
# ---------------------------------------------------------------------------
TWITTER_QUERIES = [
    "Zomato",
    "Blinkit",
    "HyperPure",
    "\"District app\" Zomato",
    "Zomato Gold",
    "Zomato Pro",
    "Zomato refund",
    "Zomato support",
    "Grofers",
]
TWITTER_MONTHS_BACK = 12   # Last 12 months
TWITTER_PER_QUERY   = 600  # Rows to attempt per query (~5,400 total buffer)

# ---------------------------------------------------------------------------
# Quora
# ---------------------------------------------------------------------------
QUORA_QUERIES = [
    "Zomato delivery experience",
    "Zomato Gold worth it",
    "Blinkit experience review",
    "HyperPure review quality",
    "District app Zomato review",
    "Zomato vs Swiggy",
    "Zomato support refund",
    "Grofers Blinkit review",
    "Zomato Pro membership",
    "Zomato restaurant partner",
]
QUORA_PER_QUERY = 350  # Rows to attempt per query

# ---------------------------------------------------------------------------
# News Article Comments
# ---------------------------------------------------------------------------
NEWS_SOURCES = {
    "Economic Times": {
        "search_url": "https://economictimes.indiatimes.com/searchresult.cms?query={query}",
        "domain": "economictimes.indiatimes.com",
    },
    "Times of India": {
        "search_url": "https://timesofindia.indiatimes.com/topic/{query}",
        "domain": "timesofindia.indiatimes.com",
    },
    "Moneycontrol": {
        "search_url": "https://www.moneycontrol.com/news/tags/{query}/",
        "domain": "moneycontrol.com",
    },
    "YourStory": {
        "search_url": "https://yourstory.com/search?q={query}",
        "domain": "yourstory.com",
    },
}
NEWS_QUERIES   = ["Zomato", "Blinkit", "HyperPure", "District Zomato", "Zomato Gold"]
NEWS_PER_QUERY = 100  # Comments to attempt per query per site

# ---------------------------------------------------------------------------
# Row targets (Twitter is now included; buffer built in for shortfalls)
# ---------------------------------------------------------------------------
ROW_TARGETS = {
    "Reddit":          17000,   # original 15k + 2k buffer
    "Google Play":     20000,   # original 18k + 2k buffer
    "Apple App Store": 13500,   # original 12k + 1.5k buffer
    "Twitter":          5500,   # original 5k + 500 buffer
    "Quora":            3500,   # original 3k + 500 buffer
    "News":             2000,   # original 2k
}

# ---------------------------------------------------------------------------
# Keyword → Product_Tag mapping  (longer/more-specific phrases checked first)
# ---------------------------------------------------------------------------
KEYWORD_PRODUCT_MAP = [
    ("zomato gold",         "Zomato Gold"),
    ("zomato pro",          "Zomato"),
    ("zomato membership",   "Zomato"),
    ("zomato refund",       "Zomato"),
    ("zomato support",      "Zomato"),
    ("zomato restaurant",   "Zomato"),
    ("zomato partner",      "Zomato"),
    ("district by zomato",  "District"),
    ("district app",        "District"),
    ("hyperpure",           "HyperPure"),
    ("hyper pure",          "HyperPure"),
    ("blinkit",             "Blinkit"),
    ("grofers",             "Blinkit"),
    ("zomato",              "Zomato"),
]

OUTPUT_PATH = r"output\zomato_data.xlsx"

COLUMNS = [
    "Post_ID", "Platform", "Source", "Date",
    "Username", "Title", "Text", "Score",
    "Product_Tag", "URL",
]
