# Data Dictionary

This folder contains a sample of 100 rows from the complete 45,000+ row dataset to demonstrate the data structure, cleanliness, and NLP enrichment process. The full dataset is excluded from version control due to size constraints.

## Columns

- `Review_ID`: Unique alphanumeric identifier for each review/post.
- `Platform`: The source platform (e.g., Apple App Store, Google Play Store, Reddit).
- `Source`: Specific country storefront (e.g., App Store — IN) or subreddit.
- `Date`: Date the review was posted (DD/MM/YYYY). Filtered strictly for Dec 1, 2025 onwards.
- `Username`: The masked or raw username of the reviewer.
- `Title`: The title of the review (if applicable, e.g., on App Store).
- `Text`: The actual body text of the review. 100% unique (no duplicates).
- `Score`: The star rating (1-5) given by the user, if applicable.
- `Product_Tag`: The specific brand (Zomato, Blinkit, District).
- `URL`: Direct link to the source review for verification.
- `Sentiment`: The VADER-calculated sentiment (Positive, Negative, Neutral).
- `Sentiment_Score`: The VADER compound score (-1.0 to 1.0).
- `L1_Category`: The high-level product pillar (e.g., Fulfillment & Logistics, Value & Pricing).
- `L2_Specific_Issue`: The hyper-specific root cause of the complaint (e.g., Gold Delivery Radius/Distance Cap, Speed of Delivery, Item Condition & Packaging). If no specific product issue is stated, this reads `No Specific Issue Stated`.
