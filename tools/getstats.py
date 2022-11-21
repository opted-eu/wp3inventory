# script for retrieving all news sources and organizations (accepted and pending)

import json
import pydgraph
import pandas as pd
from pathlib import Path
from datetime import date
import math

query_total_entries = """
{
	sources(func: type("Source")) @filter(eq(entry_review_status, "accepted") or eq(entry_review_status, "pending")) {
        total: count(uid)
    }

    organizations(func: type("Organization")) @filter(eq(entry_review_status, "accepted") or eq(entry_review_status, "pending")) {
         total: count(uid)
    }
} """

query_sources = """
query get_sources($maximum: int, $offset: int)
{
	sources(func: type("Source"), first: $maximum, offset: $offset) @filter(eq(entry_review_status, "accepted") or eq(entry_review_status, "pending")) {
        uid expand(_all_) { uid unique_name country_code opted_scope }
    }
} """
query_organizations = """
query get_organizations($maximum: int, $offset: int)
{
    organizations(func: type("Organization"), first: $maximum, offset: $offset) @filter(eq(entry_review_status, "accepted") or eq(entry_review_status, "pending")) {
        uid expand(_all_) { uid unique_name country_code }
    }
}
"""

client_stub = pydgraph.DgraphClientStub('localhost:9080')
client = pydgraph.DgraphClient(client_stub)

total = client.txn(read_only=True).query(query_total_entries)
total = json.loads(total.json)

total_sources = total['sources'][0]['total']
total_organizations = total['sources'][0]['total']
results_maximum = 1000
offset = 0
variables = {'$maximum': results_maximum, '$offset': offset}

pages_sources = math.ceil(total_sources / results_maximum)
pages_organizations = math.ceil(total_sources / results_maximum)

sources = []

for i in range(1, pages_sources + 1):
    res = client.txn(read_only=True).query(query_sources, variables=variables)
    raw = json.loads(res.json)

    sources += raw['sources']
    variables['offset'] += results_maximum


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
results_maximum = 1000
offset = 0
variables = {'$maximum': results_maximum, '$offset': offset}

organizations = []

for i in range(1, pages_organizations + 1):
    res = client.txn(read_only=True).query(query_sources, variables=variables)
    raw = json.loads(res.json)

    organizations += raw['organizations']

    variables['offset'] += results_maximum

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
