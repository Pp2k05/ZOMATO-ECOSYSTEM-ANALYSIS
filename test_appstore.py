"""
Fetch Apple App Store bearer token from their public JS bundle,
then use the amp-api to pull reviews.
"""
import requests, re, json, time, datetime

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15',
    'Accept-Language': 'en-US,en;q=0.9',
}

def get_token():
    """Fetch bearer token embedded in Apple's App Store JS bundle."""
    # Step 1: hit the storefronts endpoint which redirects to main page with JS
    urls = [
        'https://apps.apple.com/us/genre/ios/id36',
        'https://apps.apple.com/story/id1538632801',
    ]
    for url in urls:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f'  {url[:60]} -> {r.status_code}')
        if r.status_code == 200:
            # Find JS bundle URLs
            js_urls = re.findall(r'https://[^"\']+?/modules/[^"\']+?\.js', r.text)
            print(f'  Found {len(js_urls)} JS bundle URLs')
            for js_url in js_urls[:3]:
                try:
                    jr = requests.get(js_url, headers=HEADERS, timeout=20)
                    jwt = re.search(r'eyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}', jr.text)
                    if jwt:
                        print(f'  Token found in {js_url[-40:]}')
                        return jwt.group(0)
                except Exception as e:
                    print(f'  JS fetch error: {e}')

    # Step 2: try known public token endpoint
    try:
        r2 = requests.get(
            'https://amp-api-edge.apps.apple.com/v1/catalog/us/apps/884314303',
            headers={**HEADERS, 'Origin': 'https://apps.apple.com'},
            timeout=20
        )
        print(f'  Edge API: {r2.status_code}')
        if r2.status_code != 401:
            return None
        # 401 response may contain WWW-Authenticate header with realm info
        print('  WWW-Auth:', r2.headers.get('WWW-Authenticate', '')[:100])
    except Exception as e:
        print(f'  Edge error: {e}')

    return None


def fetch_reviews_with_token(app_id, token, country='us', limit=50):
    """Fetch reviews using AMP API."""
    url = f'https://amp-api.apps.apple.com/v1/catalog/{country}/apps/{app_id}/reviews'
    params = {'l': 'en-US', 'offset': '0', 'platform': 'web', 'limit': limit}
    r = requests.get(url,
        headers={**HEADERS, 'Authorization': f'Bearer {token}', 'Origin': 'https://apps.apple.com'},
        params=params, timeout=20)
    print(f'Reviews API: {r.status_code}')
    if r.status_code == 200:
        return r.json().get('data', [])
    return []


# --- Run ---
print('=== Fetching Apple token ===')
token = get_token()
if token:
    print(f'Token: {token[:60]}...')
    reviews = fetch_reviews_with_token('884314303', token)
    print(f'Reviews fetched: {len(reviews)}')
    if reviews:
        print('Sample:', reviews[0].get('attributes', {}).get('body', '')[:100])
else:
    print('Could not get token via JS bundle')
    
    # Try node.js as last resort
    import subprocess, shutil
    node = shutil.which('node')
    print(f'Node.js available: {node}')
    npm = shutil.which('npm')
    print(f'npm available: {npm}')
