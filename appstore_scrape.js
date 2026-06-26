/**
 * appstore_scrape.js  --  Apple App Store reviews
 * Uses HELPFUL sort (works for IN store) + RECENT as fallback
 * 50 reviews per page, max 10 pages per country per sort = 500/country/sort
 */

const store = require('app-store-scraper');
const fs    = require('fs');
const path  = require('path');

const APPS = [
  {
    name: 'Zomato',
    id: '434613896',
    // IN must use HELPFUL sort; others use RECENT
    countries: [
      { cc: 'in', sort: store.sort.HELPFUL },
      { cc: 'us', sort: store.sort.RECENT  },
      { cc: 'gb', sort: store.sort.RECENT  },
      { cc: 'au', sort: store.sort.RECENT  },
      { cc: 'ca', sort: store.sort.RECENT  },
      { cc: 'sg', sort: store.sort.RECENT  },
      { cc: 'ae', sort: store.sort.RECENT  },
      { cc: 'nz', sort: store.sort.RECENT  },
      { cc: 'in', sort: store.sort.RECENT  },  // try RECENT for IN too
    ],
    target: 5000,
  },
  {
    name: 'District',
    id: '6670536058',
    countries: [
      { cc: 'in', sort: store.sort.HELPFUL },
      { cc: 'in', sort: store.sort.RECENT  },
      { cc: 'us', sort: store.sort.RECENT  },
      { cc: 'gb', sort: store.sort.RECENT  },
      { cc: 'au', sort: store.sort.RECENT  },
    ],
    target: 2000,
  },
  {
    name: 'Blinkit',
    id: '960335206',
    countries: [
      { cc: 'in', sort: store.sort.HELPFUL },
      { cc: 'in', sort: store.sort.RECENT  },
      { cc: 'us', sort: store.sort.RECENT  },
      { cc: 'gb', sort: store.sort.RECENT  },
      { cc: 'ae', sort: store.sort.RECENT  },
    ],
    target: 2000,
  },
];

const OUT_DIR = path.join(__dirname, 'output');
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR);

async function scrapeApp(appDef) {
  const { name, id, countries, target } = appDef;
  const all  = [];
  const seen = new Set();

  console.log(`\n=== ${name} (id=${id}) target=${target} ===`);

  for (const { cc, sort } of countries) {
    if (all.length >= target) break;
    const sortName = sort === store.sort.HELPFUL ? 'HELPFUL' : 'RECENT';

    for (let page = 1; page <= 10 && all.length < target; page++) {
      try {
        const results = await store.reviews({ id, country: cc, sort, page });
        if (!results || results.length === 0) break;

        let added = 0;
        for (const r of results) {
          const key = String(r.id || `${r.userName}_${r.date}_${cc}`);
          if (!seen.has(key)) {
            seen.add(key);
            const dateStr = r.updated
              ? new Date(r.updated).toLocaleDateString('en-GB', {
                  day: '2-digit', month: '2-digit', year: 'numeric'
                })
              : '';
            all.push({
              Post_ID:     key,
              Platform:    'Apple App Store',
              Source:      `App Store - ${cc.toUpperCase()}`,
              Date:        dateStr,
              Username:    r.userName || '',
              Title:       r.title    || '',
              Text:        r.text     || '',
              Score:       r.score    || '',
              Product_Tag: name,
              URL:         `https://apps.apple.com/${cc}/app/id${id}`,
            });
            added++;
          }
        }
        console.log(`  ${name} [${cc.toUpperCase()}/${sortName}] p${page}: +${added} total=${all.length}`);
        await sleep(1200);
      } catch (err) {
        console.warn(`  ${name} [${cc.toUpperCase()}/${sortName}] p${page} ERR: ${err.message}`);
        break;
      }
    }
  }

  const outFile = path.join(OUT_DIR, `appstore_${name.toLowerCase()}.json`);
  fs.writeFileSync(outFile, JSON.stringify(all, null, 2), 'utf8');
  console.log(`  [SAVED] ${name}: ${all.length} -> ${path.basename(outFile)}`);
  return all.length;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  console.log('App Store scraper v2 (HELPFUL+RECENT) -- START');
  let grand = 0;
  for (const app of APPS) {
    const n = await scrapeApp(app);
    grand += n;
  }
  console.log(`\n[DONE] Grand total: ${grand} App Store reviews`);
}

main().catch(console.error);
