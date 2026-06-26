const store = require('app-store-scraper');
const fs = require('fs');
const path = require('path');

const targets = JSON.parse(fs.readFileSync('refill_targets.json', 'utf8'));

// Wide array of countries to bypass the 500 reviews/country limit
const countries = [
  'in', 'us', 'gb', 'au', 'ca', 'sg', 'ae', 'nz', 'za', 'my', 
  'ph', 'id', 'lk', 'bd', 'np', 'pk', 'sa', 'qa', 'kw', 'om', 'bh',
  'ie', 'de', 'fr', 'nl', 'se', 'ch', 'no', 'dk', 'fi'
];

async function scrapeApp(appDef) {
  const { name, id, target, existing_ids } = appDef;
  if (target <= 0) return 0;
  
  const all = [];
  const seen = new Set(existing_ids); // Don't scrape duplicates
  
  console.log(`\n=== App Store: ${name} | Target: ${target} ===`);
  
  for (const cc of countries) {
    if (all.length >= target) break;
    
    // Try both HELPFUL and RECENT sorts
    for (const sortType of [store.sort.HELPFUL, store.sort.RECENT]) {
      if (all.length >= target) break;
      
      for (let page = 1; page <= 10; page++) {
        if (all.length >= target) break;
        
        try {
          const results = await store.reviews({ id, country: cc, sort: sortType, page });
          if (!results || results.length === 0) break;
          
          let added = 0;
          for (const r of results) {
            const key = String(r.id || `${r.userName}_${r.date}_${cc}`);
            if (!seen.has(key)) {
              seen.add(key);
              
              const dateStr = r.updated ? new Date(r.updated).toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '';
              all.push({
                Review_ID: key,
                Platform: 'Apple App Store',
                Source: `App Store - ${cc.toUpperCase()}`,
                Date: dateStr,
                Username: r.userName || '',
                Title: r.title || '',
                Text: r.text || '',
                Score: r.score || '',
                Product_Tag: name,
                URL: `https://apps.apple.com/${cc}/app/id${id}`
              });
              added++;
              if (all.length >= target) break;
            }
          }
          console.log(`  [${cc.toUpperCase()}] p${page}: +${added} (Total: ${all.length}/${target})`);
          await new Promise(r => setTimeout(r, 1000));
        } catch (e) {
          break; // Usually 400 error if no more reviews for that country/page
        }
      }
    }
  }
  
  fs.writeFileSync(`output/appstore_refill_${name.toLowerCase()}.json`, JSON.stringify(all, null, 2));
  return all.length;
}

async function main() {
  for (const app of targets) {
    await scrapeApp(app);
  }
}

main().catch(console.error);
