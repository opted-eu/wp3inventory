# simple script for transforming raw dgraph json to csv
# Query for getting all pending news sources:

# {
# 	q(func: type(Source)) @filter(eq(entry_review_status, "pending") OR eq(entry_review_status, "draft")) {
# 		expand(_all_) { uid unique_name name user_displayname }
#     published_by: ~publishes { uid unique_name name }
#   }
# }

import json
import pandas as pd

with open('tools/relitest.json') as f:
    raw = json.load(f)

raw = raw['data']['q']

# manual normalization

for entry in raw:
    entry['channel'] = entry['channel']['unique_name']
    entry['other_names'] = ", ".join(entry.get('other_names', []))
    entry['languages'] = ", ".join(entry.get('languages', []))
    entry['publication_kind'] = ", ".join(entry.get('publication_kind', []))
    entry['country'] = ", ".join([country['name'] for country in entry.get('country', [])])
    entry['subunit'] = ", ".join([subunit['name'] for subunit in entry.get('geographic_scope_subunit', [])])
    entry['entry_added_email'] = entry['entry_added']['email']
    entry['entry_added_username'] = entry['entry_added']['user_displayname']
    try:
        entry['published_by'] = ", ".join([org['name'] for org in entry['published_by']])
    except:
        entry['published_by'] = ""
    if entry.get('publication_cycle_weekday'):
        for weekday in entry.get('publication_cycle_weekday'):
            entry['publication_cycle_weekday_' + str(weekday)] = 'yes'

df = pd.DataFrame(raw)
filt = df.entry_added_username == 'Paul Balluff'
df = df[~filt]
df.to_csv('tools/relitest.csv')