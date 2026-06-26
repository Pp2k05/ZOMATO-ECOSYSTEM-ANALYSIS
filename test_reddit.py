from scrapers.reddit_scraper import scrape_reddit
print('Testing Reddit scraper - fetching 10 rows...')
rows = scrape_reddit(10)
print(f'Got {len(rows)} rows')
for r in rows[:3]:
    src = r.get('Source','')
    txt = str(r.get('Text',''))[:60]
    dt  = r.get('Date','')
    print(f'  r/{src} | {dt} | {txt}')
