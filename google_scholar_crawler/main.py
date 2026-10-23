from scholarly import scholarly, DOSException, MaxTriesExceededException
from contextlib import contextmanager
import jsonpickle
import json
from datetime import datetime
import os
import signal
import sys

google_scholar_id = os.environ['GOOGLE_SCHOLAR_ID']
# Successful fetches take a few seconds; when Google Scholar blocks the
# runner, scholarly either gives up or retries forever
time_limit_seconds = 90


class AttemptTimeout(BaseException):
    """A BaseException so scholarly's `except Exception` retry loops can't swallow it."""


def on_alarm(signum, frame):
    raise AttemptTimeout()


signal.signal(signal.SIGALRM, on_alarm)


@contextmanager
def time_limit(seconds):
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def fetch_author():
    author: dict = scholarly.search_author_id(google_scholar_id)
    scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
    return author


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
    print("Fetching author data...", file=sys.stderr)
    with time_limit(time_limit_seconds):
        save(fetch_author())
except (AttemptTimeout, MaxTriesExceededException, DOSException) as e:
    # Blocked by Google Scholar: not a bug, so leave the published data
    # as it is and let a later scheduled run try again
    print(f"Google Scholar blocked this runner ({type(e).__name__}); keeping the existing data", file=sys.stderr)
