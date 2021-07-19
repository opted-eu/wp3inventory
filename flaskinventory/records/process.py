from flaskinventory.records.validators import InventoryValidationError
from flaskinventory.auxiliary import icu_codes

payment_model = ['free', 'soft paywall', 'subscription', 'none']
contains_ads = ['yes', 'no', 'non subscribers', 'none']
ownership_kind = ['public ownership', 'private ownership', 'unknown', 'none']
special_interest = ['yes', 'no']

publication_cycle = ['continuous', 'daily', 'multiple times per week',
                     'weekly', 'twice a month', 'monthly', 'none']
geographic_scope = ['multinational', 'national', 'subnational', 'none']

def process_print(json):

    new_print = {
        'channel': {}
    }

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

    if json.get('ownership_kind'):
        if json.get('ownership_kind').lower() in ownership_kind:
            new_print['ownership_kind'] = json.get('ownership_kind').lower()
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "ownership_kind"')

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
            if new_print['publication_cycle'] in ["mulitple times per week"]:
                days_list = []
                for item in json.keys():
                    if item.startswith('publication_cycle_weekday'):
                        if json[item].lower() == 'yes':
                            days_list.append(int(item.replace('publication_cycle_weekday', '')))
                if json.get('publication_cycle_na_weekday'):
                    if json.get('publication_cycle_na_weekday').lower() == 'yes':
                        days_list = []
                new_print["publication_cycle_weekday"] = days_list
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "publication_cycle"')

    if json.get('geographic_scope'):
        if json.get('geographic_scope').lower() in geographic_scope:
            new_print['geographic_scope'] = json.get('geographic_scope').lower()
            if new_print['geographic_scope'] == 'multinational':
                if json.get('geographic_scope_multiple'):
                    new_print['geographic_scope_countries'] = []
                    for country in json.get('geographic_scope_multiple'):
                        if country.startswith('0x'):
                            new_print['geographic_scope_countries'].append({'uid': country})
                        else:
                            # write geocoding function
                            # add new subunit / country
                            continue
            elif new_print['geographic_scope'] == 'national':
                if json.get('geographic_scope_single'):
                    if json.get('geographic_scope_single').startswith('0x'):
                        new_print['geographic_scope_countries'] = [{'uid': json.get('geographic_scope_single')}]
                    else:
                        raise InventoryValidationError('Invalid Data! geographic_scope_single not in uid')
            elif new_print['geographic_scope'] == 'subnational':
                if json.get('geographic_scope_single'):
                    if json.get('geographic_scope_single').startswith('0x'):
                        new_print['geographic_scope_countries'] = [{'uid': json.get('geographic_scope_single')}]
                    else:
                        raise InventoryValidationError('Invalid Data! geographic_scope_single not in uid')
                if json.get('geographic_scope_subunit'):
                    # write geocoding function
                    # add new subunit
                    print('todo!')
        else:
            raise InventoryValidationError(
                'Invalid data! Unknown value in "geographic_scope"')
        
    if json.get('languages'):
        if type(json.get('languages')) == list:
            new_print['languages'] = [item.lower() for item in json.get('languages') if item.lower() in icu_codes.keys()]
        else:
            if json.get('languages').lower() in icu_codes.keys():
                new_print['languages'] = [json.get('languages').lower()]
            




        
                    




    # generate unique name
    # check if unique_name is free

    # add new source to dgraph

    # retrieve uid of new source
    # add relationship: publishes_org
    if json.get('publishes_org'):
        if type(json.get('publishes_org')) == list:
            print('later')
        else:
            if json.get('publishes_org').startswith('0x'):
                print('later')

    if json.get('publishes_person'):
        if type(json.get('publishes_person')) == list:
            print('later')
        else:
            if json.get('publishes_person').startswith('0x'):
                print('later')
