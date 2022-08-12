# script for retrieving all news sources and organizations (accepted and pending)

import json
import pydgraph
import pandas as pd
from pathlib import Path
from datetime import date

query_string = """
{
	sources(func: type("Source")) @filter(eq(entry_review_status, "accepted") or eq(entry_review_status, "pending")) {
        uid expand(_all_) { uid unique_name country_code opted_scope }
    }

    organizations(func: type("Organization")) @filter(eq(entry_review_status, "accepted") or eq(entry_review_status, "pending")) {
        uid expand(_all_) { uid unique_name country_code }
    }
}
"""

client_stub = pydgraph.DgraphClientStub('localhost:9080')
client = pydgraph.DgraphClient(client_stub)
res = client.txn(read_only=True).query(query_string)
raw = json.loads(res.json)

sources = raw['sources']
output = Path.home() / f'sources_dump_{date.today()}.json'

with open(output, 'w') as f:
    json.dump(sources, f)

# manual normalization
for entry in sources:
    try:
        entry['entry_added'] = entry['entry_added']['uid']
        entry['channel'] = entry['channel']['unique_name']
        entry['other_names'] = ", ".join(entry.get('other_names', []))
        entry['languages'] = ", ".join(entry.get('languages', []))
        entry['publication_kind'] = ", ".join(entry.get('publication_kind', []))
        entry['subunit'] = ", ".join([subunit['unique_name'] for subunit in entry.get('geographic_scope_subunit', [])])
        if entry.get('publication_cycle_weekday'):
            for weekday in entry.get('publication_cycle_weekday'):
                entry['publication_cycle_weekday_' + str(weekday)] = 'yes'
        if entry.get('country'):
            for country in entry['country']:
                if country.get('opted_scope', False):
                    if country.get('unique_name'):
                        entry[country['unique_name']] = 1
                    if country.get('country_code'):
                        entry[f"country_{country['country_code']}"] = 1
            entry['country'] = ", ".join([country['unique_name'] for country in entry['country']])

    except Exception as e:
        print(entry['unique_name'])
        print(entry.get('uid'), e)

df = pd.DataFrame(sources)
output = Path.home() / f'sources_flattened_{date.today()}.csv'
df.to_csv(output)

## Organizations


organizations = raw['organizations']
output = Path.home() / f'organizations_dump_{date.today()}.json'

with open(output, 'w') as f:
    json.dump(organizations, f)

# manual normalization
for entry in organizations:
    try:
        entry['entry_added'] = entry['entry_added']['uid']
        entry['other_names'] = ", ".join(entry.get('other_names', []))
        if entry.get('country'):
            for country in entry['country']:
                if country.get('unique_name'):
                    entry[country['unique_name']] = 1
                if country.get('country_code'):
                    entry[f"country_{country['country_code']}"] = 1
            entry['country'] = ", ".join([country['country_code'] for country in entry['country']])
    except Exception as e:
        print(entry['unique_name'])
        print(entry.get('uid'), e)

df = pd.DataFrame(organizations)
output = Path.home() / f'organizations_flattened_{date.today()}.csv'
df.to_csv(output)
