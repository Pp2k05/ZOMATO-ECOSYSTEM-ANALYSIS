import pandas as pd
import numpy as np

def score_accuracy(brand, file_path):
    print(f"\nEvaluating Accuracy for {brand}...")
    df = pd.read_excel(file_path, sheet_name='Raw Data')
    
    # Filter out uncategorized for accuracy scoring
    categorized = df[~df['L1_Category'].str.contains('Uncategorized', na=False)]
    total_categorized = len(categorized)
    
    if total_categorized == 0:
        print("No categorized data found.")
        return
        
    # Heuristic 1: Sentiment-Category Alignment
    # If a row is tagged with a historically negative L2 issue (e.g., Late Delivery, Food Quality, Fraud)
    # but the sentiment is strongly Positive, it might be a false positive (sarcasm or mis-tag).
    
    # Define inherently positive/negative L1/L2 tags based on our taxonomy
    positive_tags = ['General Convenience & Praise', 'Fast Delivery', 'Good Ambience']
    
    # We will look for contradictions
    contradictions = 0
    
    for _, row in categorized.iterrows():
        sentiment = row.get('Sentiment', 'Neutral')
        l2_issues = str(row.get('L2_Specific_Issue', ''))
        
        # Check if it's a Praise tag but marked Negative
        is_praise = any(p in l2_issues for p in positive_tags)
        if is_praise and sentiment == 'Negative':
            contradictions += 1
            continue
            
        # Check if it's a clear Complaint (most of our specific tags are complaints)
        # We'll assume if it's NOT in positive_tags and NOT a general competitor comparison, it's a complaint/issue.
        # If a clear issue has a Positive sentiment (and the score isn't naturally 4/5 stars overriding it), it's a contradiction.
        # Note: We forced 1/2 star to negative in our tagger, so sentiment is usually aligned.
        # Let's check for pure text-based contradictions where Score wasn't a factor.
        is_complaint = not is_praise and "Competitor" not in l2_issues and "Promotions" not in l2_issues
        # We only count it as a contradiction if sentiment is strongly Positive
        if is_complaint and sentiment == 'Positive':
            contradictions += 1
            
    # Calculate Confidence/Accuracy Score
    alignment_accuracy = ((total_categorized - contradictions) / total_categorized) * 100
    
    print(f"Total Categorized Rows: {total_categorized}")
    print(f"Potential False Positives (Sarcasm/Mis-tags): {contradictions}")
    print(f"Estimated Taxonomy Accuracy: {alignment_accuracy:.2f}%")

if __name__ == "__main__":
    score_accuracy("Zomato", "output/zomato_data_enriched.xlsx")
    score_accuracy("Blinkit", "output/blinkit_data_enriched.xlsx")
    score_accuracy("District", "output/district_data_enriched.xlsx")
