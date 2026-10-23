from scholarly import scholarly
from scholarly._navigator import Navigator
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
# A run through it costs 25 credits (one Google request) and the free plan
# has 1,000 a month, so only use it once the published data is a day old.
proxy_after_hours = 24
direct_time_limit = 90
proxy_time_limit = 300
# ScraperAPI keeps retrying Google for up to 70s before answering
scraperapi_timeout = 90
scraperapi_attempts = 3


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


scraperapi_pages = {}


def get_page_via_scraperapi(pagerequest, premium=False):
    # Replaces scholarly's own fetching, which gives ScraperAPI only 60s.
    # scholarly asks for the profile page twice, so reuse the first response.
    if pagerequest in scraperapi_pages:
        return scraperapi_pages[pagerequest]
    for attempt in range(1, scraperapi_attempts + 1):
        try:
            resp = requests.get('https://api.scraperapi.com/',
                                params={'api_key': scraper_api_key, 'url': pagerequest},
                                timeout=scraperapi_timeout)
        except requests.RequestException as e:
            # Only the type: the message can include the request URL with the key
            print(f"ScraperAPI attempt {attempt}: {type(e).__name__}", file=sys.stderr)
            continue
        print(f"ScraperAPI attempt {attempt}: HTTP {resp.status_code}", file=sys.stderr)
        if resp.status_code == 200:
            scraperapi_pages[pagerequest] = resp.text
            return resp.text
        if resp.status_code in (401, 403):
            raise RuntimeError("ScraperAPI rejected the key or the credits are used up")
    raise RuntimeError(f"ScraperAPI failed {scraperapi_attempts} times")


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
        # Every scholarly page request goes through this one shared Navigator
        Navigator()._get_page = get_page_via_scraperapi
        save(fetch_author())
except (Exception, AttemptTimeout) as e:
    print(f"ScraperAPI request failed ({type(e).__name__}: {e})", file=sys.stderr)
    sys.exit(1)
