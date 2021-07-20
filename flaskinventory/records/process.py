from flaskinventory.records.validators import InventoryValidationError
from flaskinventory.auxiliary import icu_codes
from flaskinventory.records.external import geocode
from flaskinventory import dgraph
from slugify import slugify
import secrets

import datetime

payment_model = ['free', 'soft paywall', 'subscription', 'none']
contains_ads = ['yes', 'no', 'non subscribers', 'none']
ownership_kind = ['public ownership', 'private ownership', 'unknown', 'none']
special_interest = ['yes', 'no']

publication_cycle = ['continuous', 'daily', 'multiple times per week',
                     'weekly', 'twice a month', 'monthly', 'none']
geographic_scope = ['multinational', 'national', 'subnational', 'none']


def process_print(json):

    new_print = {
        'uid': "_:newsource",
        'channel': {}
    }
    mutation = []

    if json.get('name'):
        new_print['name'] = json.get('name')
    else:
        raise InventoryValidationError('Invalid data! "name" not specified.')

    if json.get('channel_uid').startswith('0x'):
        new_print['channel']['uid'] = json.get('channel_uid')
    else:
        raise InventoryValidationError(
            'Invalid data! uid of channel not defined')

    if json.get('other_names'):
        new_print['other_names'] = json.get('other_names').split(',')

    if json.get('channel_epaper'):
        new_print['channel_epaper'] = json.get('channel_epaper')

    if json.get('founded'):
        try:
            founded = int(json.get('founded'))
            if founded < 1700:
                raise InventoryValidationError(
                    'Invalid data! "founded" too small')
            if founded > 2100:
                raise InventoryValidationError(
                    'Invalid data! "founded" too large')
            new_print['founded'] = founded
        except ValueError:
            raise InventoryValidationError(
                'Invalid Data! Cannot parse "founded" to int.')

    if json.get('payment_model'):
        if json.get('payment_model').lower() in payment_model:
            new_print['payment_model'] = json.get('payment_model').lower()
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "payment_model"')

    if json.get('contains_ads'):
        if json.get('contains_ads').lower() in contains_ads:
            new_print['contains_ads'] = json.get('contains_ads').lower()
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "contains_ads"')

    # add relationship: publishes_org
    mutation += parse_org(json)
    mutation += parse_person(json)

    if json.get('publication_kind'):
        if type(json.get('publication_kind')) == list:
            new_print['publication_kind'] = [item.lower()
                                             for item in json.get('publication_kind')]
        else:
            new_print['publication_kind'] = json.get(
                'publication_kind').lower()

    if json.get('special_interest'):
        if json.get('special_interest').lower() in special_interest:
            new_print['special_interest'] = json.get(
                'special_interest').lower()
            if json.get('special_interest') == 'yes':
                if json.get('topical_focus'):
                    if type(json.get('topical_focus')) == list:
                        new_print['topical_focus'] = [item.lower()
                                                      for item in json.get('topical_focus')]
                    else:
                        new_print['topical_focus'] = json.get(
                            'topical_focus').lower()
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "special_interest"')

    if json.get('publication_cycle'):
        if json.get('publication_cycle').lower() in publication_cycle:
            new_print['publication_cycle'] = json.get(
                'publication_cycle').lower()
            if new_print['publication_cycle'] in ["multiple times per week", "weekly"]:
                days_list = []
                for item in json.keys():
                    if item.startswith('publication_cycle_weekday_'):
                        if json[item].lower() == 'yes':
                            if 'none' in item:
                                days_list = []
                                break
                            days_list.append(
                                int(item.replace('publication_cycle_weekday_', '')))
                new_print["publication_cycle_weekday"] = days_list
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "publication_cycle"')

    if json.get('geographic_scope'):
        if json.get('geographic_scope').lower() in geographic_scope:
            new_print['geographic_scope'] = json.get(
                'geographic_scope').lower()
            if new_print['geographic_scope'] == 'multinational':
                if json.get('geographic_scope_multiple'):
                    new_print['geographic_scope_countries'] = []
                    for country in json.get('geographic_scope_multiple'):
                        if country.startswith('0x'):
                            new_print['geographic_scope_countries'].append(
                                {'uid': country})
                        else:
                            # write geocoding function
                            # add new subunit / country
                            continue
            elif new_print['geographic_scope'] == 'national':
                if json.get('geographic_scope_single'):
                    if json.get('geographic_scope_single').startswith('0x'):
                        new_print['geographic_scope_countries'] = [
                            {'uid': json.get('geographic_scope_single')}]
                    else:
                        raise InventoryValidationError(
                            'Invalid Data! "geographic_scope_single" not uid')
            elif new_print['geographic_scope'] == 'subnational':
                if json.get('geographic_scope_single'):
                    if json.get('geographic_scope_single').startswith('0x'):
                        new_print['geographic_scope_countries'] = [
                            {'uid': json.get('geographic_scope_single')}]
                    else:
                        raise InventoryValidationError(
                            'Invalid Data! "geographic_scope_single" not uid')
                else:
                    raise InventoryValidationError(
                        'Invalid Data! need to specify at least one country!')
                new_print['geographic_scope_subunit'] = parse_subunit(json)
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "geographic_scope"')
    else:
        raise InventoryValidationError(
            'Invalid data! "geographic_scope" is required')

    if json.get('languages'):
        if type(json.get('languages')) == list:
            new_print['languages'] = [item.lower() for item in json.get(
                'languages') if item.lower() in icu_codes.keys()]
        else:
            if json.get('languages').lower() in icu_codes.keys():
                new_print['languages'] = [json.get('languages').lower()]

    if json.get('audience_size_subscribers'):
        new_print['audience_size|subscribers'] = int(
            json.get('audience_size_subscribers'))
        if json.get('audience_size_year'):
            new_print['audience_size'] = str(
                int(json.get('audience_size_year')))
        else:
            new_print['audience_size'] = str(datetime.date.today())
        if json.get('audience_size_datafrom'):
            new_print['audience_size|datafrom'] = json.get(
                'audience_size_datafrom')
        else:
            new_print['audience_size|datafrom'] = "unknown"

    mutation += parse_archives(json)
    mutation += parse_datasets(json)

    if json.get('entry_notes'):
        new_print['entry_notes'] = json.get('entry_notes')

    mutation += parse_related(json)

    # generate unique name

    if new_print.get('geographic_scope_subunit'):
        if 'uid' in new_print['geographic_scope_subunit'][0].keys():
            new_print["unique_name"] = source_unique_name(
                json['name'], channel=json['channel'], country_uid=new_print['geographic_scope_subunit'][0]['uid'])
        else:
            new_print["unique_name"] = source_unique_name(
                json['name'], channel=json['channel'], country=new_print['geographic_scope_subunit'][0]['name'])

    elif 'uid' in new_print['geographic_scope_countries'][0].keys():
        new_print["unique_name"] = source_unique_name(
            json['name'], json['channel'], country_uid=new_print['geographic_scope_countries'][0]['uid'])
    else:
        new_print["unique_name"] = source_unique_name(
            json['name'], json['channel'], country="unknown")

    mutation.append(new_print)

    return mutation


def source_unique_name(name, channel=None, channel_uid=None, country=None, country_uid=None):
    name = slugify(name, separator="_")
    channel = slugify(channel, separator="_")
    if country_uid:
        country = dgraph.query(
            f'''{{ q(func: uid({country_uid})) {{ unique_name }} }}''')
        country = country['q'][0]['unique_name']

    if channel_uid:
        channel = dgraph.query(
            f'''{{ q(func: uid({channel_uid})) {{ unique_name }} }}''')
        channel = country['q'][0]['unique_name']

    country = slugify(country, separator="_")
    query_string = f'''{{
                        field1 as var(func: eq(unique_name, "{name}_{channel}"))
                        field2 as var(func: eq(unique_name, "{name}_{country}_{channel}"))
                    
                        data1(func: uid(field1)) {{
                                unique_name
                                uid
                        }}
                    
                        data2(func: uid(field2)) {{
                            unique_name
                            uid
                        }}
                        
                    }}'''

    result = dgraph.query(query_string)

    if len(result['data1']) == 0:
        return f'{name}_{channel}'
    elif len(result['data2']) == 0:
        return f'{name}_{country}_{channel}'
    else:
        return f'{name}_{country}_{channel}_{secrets.token_urlsafe(4)}'


def parse_org(data):
    orgs = []
    if data.get('publishes_org'):
        if type(data.get('publishes_org')) != list:
            org_list = [data.get('publishes_org')]
        else:
            org_list = data.get('publishes_org')

        for item in org_list:
            org = {'publishes': [{'uid': "_:newsource"}],
                   'is_person': False}
            if item.startswith('0x'):
                org['uid'] = item

            else:
                org['name'] = item,
                org['dgraph.type'] = "Organization"
            if data.get('ownership_kind'):
                if data.get('ownership_kind').lower() in ownership_kind:
                    org["ownership_kind"] = data.get('ownership_kind').lower()
                else:
                    raise InventoryValidationError(
                        'Invalid data! Unknown value in "ownership_kind"')
            orgs.append(org)
    return orgs


def parse_person(data):
    persons = []
    if data.get('publishes_person'):
        if type(data.get('publishes_person')) != list:
            person_list = [data.get('publishes_person')]
        else:
            person_list = data.get('publishes_person')

        for item in person_list:
            pers = {'publishes': [{'uid': "_:newsource"}],
                    'is_person': True}
            if item.startswith('0x'):
                pers['uid'] = item
            else:
                pers['name'] = item,
                pers['dgraph.type'] = "Organization"
            if data.get('ownership_kind'):
                if data.get('ownership_kind').lower() in ownership_kind:
                    pers["ownership_kind"] = data.get('ownership_kind').lower()
                else:
                    raise InventoryValidationError(
                        'Invalid data! Unknown value in "ownership_kind"')
            persons.append(pers)
    return persons


def parse_archives(data):
    archives = []
    if data.get('archive_sources_included'):
        if type(data.get('archive_sources_included')) != list:
            archive_list = [data.get('archive_sources_included')]
        else:
            archive_list = data.get('archive_sources_included')

        for item in archive_list:
            arch = {'sources_included': [{'uid': '_:newsource'}]}
            if item.startswith('0x'):
                arch['uid'] = item

            else:
                arch['name'] = item,
                arch['dgraph.type'] = "Archive"
                arch['entry_added'] = {'name': 'unknown'}
                arch['entry_added|timestamp'] = datetime.datetime.now(
                    datetime.timezone.utc).isoformat()
                arch['entry_added|ip'] = "0.0.0.0"
                arch['entry_review_status'] = "pending"
            archives.append(arch)
    return archives


def parse_datasets(data):
    datasets = []
    if data.get('dataset_sources_included'):
        if type(data.get('dataset_sources_included')) != list:
            dataset_list = [data.get('dataset_sources_included')]
        else:
            dataset_list = data.get('dataset_sources_included')

        for item in dataset_list:
            dset = {'sources_included': [{'uid': '_:newsource'}]}
            if item.startswith('0x'):
                dset['uid'] = item

            else:
                dset['name'] = item,
                dset['dgraph.type'] = "Dataset"
                dset['entry_added'] = {'name': 'unknown'}
                dset['entry_added|timestamp'] = datetime.datetime.now(
                    datetime.timezone.utc).isoformat()
                dset['entry_added|ip'] = "0.0.0.0"
                dset['entry_review_status'] = "pending"
            datasets.append(dset)
    return datasets


def parse_related(data):
    related = []
    if data.get('related_sources'):
        if type(data.get('related_sources')) != list:
            related_list = [data.get('related_sources')]
        else:
            related_list = data.get('related_sources')
        for item in related_list:
            rel_source = {'related': [{'uid': '_:newsource'}]}
            if item.startswith('0x'):
                rel_source['uid'] = item
            else:
                if data.get(f'newsource_{item}'):
                    rel_source['name'] = item
                    rel_source['unique_name'] = secrets.token_urlsafe(8)
                    rel_source['dgraph.type'] = 'Source'
                    rel_source['channel'] = {
                        'uid': data.get(f'newsource_{item}')}
                else:
                    # just discard data if no channel is defined
                    continue
            related.append(rel_source)

    return related


def resolve_geographic_name(query):
    geo_result = geocode(query)
    if geo_result:
        dql_string = f'''{{ q(func: eq(country_code, {geo_result.json['country_code']}) {{ uid }} }}'''
        dql_result = dgraph.query(dql_string)
        try:
            country_uid = dql_result['q'][0]['uid']
        except Exception:
            raise InventoryValidationError('Country not found in inventory!')
        other_name = geo_result.json.get('city', '')
        geo_data = {'type': 'point', 'coordinates': [
            geo_result.json.get('lng'), geo_result.json.get('lat')]}
        return {'country_uid': country_uid, 'other_name': other_name, 'geo_data': geo_data, 'country_code': geo_result.json['country_code']}
    else:
        return False


def parse_subunit(data):
    subunits = []
    if data.get('geographic_scope_subunit'):
        if type(data.get('geographic_scope_subunit')) != list:
            subunit_list = [data.get('geographic_scope_subunit')]
        else:
            subunit_list = data.get('geographic_scope_subunit')

        for item in subunit_list:
            if item.startswith('0x'):
                subunit = {'uid': item}
            else:
                geo_query = resolve_geographic_name(item)
                if geo_query:
                    subunit = {'name': item,
                               'dgraph.type': 'Subunit',
                               'country': [{'uid': geo_query['country_uid']}],
                               'other_names': [geo_query['other_name']],
                               'location_point': geo_query['geo_data'],
                               'unique_name': f"{slugify(item)}_{geo_query['country_code']}"}

            subunits.append(subunit)
    return subunits


# turn this process into a class
# add method for generic meta data (entry_added)
# keep track of user

# unique names of related & new sources are generated later (after reviewed)
