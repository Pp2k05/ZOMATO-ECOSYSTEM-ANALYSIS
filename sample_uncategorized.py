import pandas as pd
import random

with open("uncategorized_sample.txt", "w", encoding="utf-8") as f:
    for brand, fname in [('Zomato', 'zomato'), ('Blinkit', 'blinkit'), ('District', 'district')]:
        f.write(f'\n=== {brand} UNCATEGORIZED ===\n')
        df = pd.read_excel(f'output/{fname}_data_enriched.xlsx', sheet_name='Raw Data')
        uncat = df[df['L1_Category'].str.contains('Uncategorized', na=False)]
        
        samples = uncat['Text'].dropna().tolist()
        if len(samples) > 20:
            samples = random.sample(samples, 20)
            
        for i, text in enumerate(samples):
            f.write(f'{i+1}. {text[:200].replace(chr(10), " ")}...\n')
