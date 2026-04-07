from scholarly import scholarly
import jsonpickle
import json
from datetime import datetime
import os
import time
import sys

google_scholar_id = os.environ['GOOGLE_SCHOLAR_ID']
author = None
max_retries = 5

# Try multiple times with increasing delays to handle temporary blocks
for attempt in range(max_retries):
    try:
        print(f"Attempt {attempt + 1}/{max_retries}: Fetching author data...", file=sys.stderr)
        author: dict = scholarly.search_author_id(google_scholar_id)
        scholarly.fill(author, sections=['basics', 'indices', 'counts', 'publications'])
        
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
        sys.exit(0)
        
    except Exception as e:
        print(f"Attempt {attempt + 1} failed: {e}", file=sys.stderr)
        if attempt < max_retries - 1:
            wait_time = 10 * (2 ** attempt)  # Exponential backoff: 10, 20, 40, 80, 160 seconds
            print(f"Waiting {wait_time} seconds before retry...", file=sys.stderr)
            time.sleep(wait_time)
        else:
            print(f"All {max_retries} attempts failed", file=sys.stderr)
            sys.exit(1)
