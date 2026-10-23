from scholarly import scholarly, ProxyGenerator
from contextlib import contextmanager
import jsonpickle
import json
from datetime import datetime
import os
import requests
import signal
import sys

google_scholar_id = os.environ['GOOGLE_SCHOLAR_ID']
scraper_api_key = os.environ.get('SCRAPER_API_KEY')

# Google Scholar blocks most GitHub runners, so ScraperAPI is the fallback.
# A run through it costs 50 credits (2 requests x 25) and the free plan has
# 1,000 a month, so only use it once the published data is a day old.
proxy_after_hours = 24
direct_time_limit = 120
proxy_time_limit = 240


class AttemptTimeout(BaseException):
    """A BaseException so scholarly's `except Exception` retry loops can't swallow it."""


def on_alarm(signum, frame):
    raise AttemptTimeout()


signal.signal(signal.SIGALRM, on_alarm)


@contextmanager
def time_limit(seconds):
    # When blocked, scholarly retries forever instead of raising
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def fetch_author():
    author: dict = scholarly.search_author_id(google_scholar_id)
    scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
    return author


def hours_since_last_update():
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not repo:
        return float('inf')
    try:
        url = f'https://raw.githubusercontent.com/{repo}/google-scholar-stats/gs_data.json'
        updated = requests.get(url, timeout=30).json()['updated']
        return (datetime.now() - datetime.fromisoformat(updated)).total_seconds() / 3600
    except Exception:
        return float('inf')


def save(author):
    name = author['name']
    author['updated'] = str(datetime.now())
    author['publications'] = {v['author_pub_id']:v for v in author['publications']}
    print(json.dumps(author, indent=2))
    os.makedirs('results', exist_ok=True)
    with open(f'results/gs_data.json', 'w') as outfile:
        json.dump(author, outfile, ensure_ascii=False)

    shieldio_data = {
      "schemaVersion": 1,
      "label": "citations",
      "message": f"{author['citedby']}",
    }
    with open(f'results/gs_data_shieldsio.json', 'w') as outfile:
        json.dump(shieldio_data, outfile, ensure_ascii=False)

    print(f"Successfully updated citation data for {name}", file=sys.stderr)


try:
    print("Fetching author data directly...", file=sys.stderr)
    with time_limit(direct_time_limit):
        save(fetch_author())
    sys.exit(0)
except (Exception, AttemptTimeout) as e:
    print(f"Direct request failed ({type(e).__name__}); Google Scholar is likely blocking this runner", file=sys.stderr)

age = hours_since_last_update()
if age < proxy_after_hours:
    print(f"Published data is {age:.1f}h old; not using ScraperAPI until it is {proxy_after_hours}h old", file=sys.stderr)
    sys.exit(0)

if not scraper_api_key:
    print("SCRAPER_API_KEY is not set, so there is no proxy to retry through", file=sys.stderr)
    sys.exit(1)

try:
    print("Retrying through ScraperAPI...", file=sys.stderr)
    with time_limit(proxy_time_limit):
        pg = ProxyGenerator()
        if not pg.ScraperAPI(scraper_api_key):
            raise RuntimeError("ScraperAPI setup failed (invalid key or no credits left)")
        # Without a secondary generator, scholarly sends profile pages
        # through random free proxies instead of ScraperAPI
        scholarly.use_proxy(pg, pg)
        # Every Google request costs credits, so keep scholarly's retries low
        scholarly.set_retries(1)
        save(fetch_author())
except (Exception, AttemptTimeout) as e:
    print(f"ScraperAPI request failed ({type(e).__name__}: {e})", file=sys.stderr)
    sys.exit(1)
