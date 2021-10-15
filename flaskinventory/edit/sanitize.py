from wtforms.validators import ValidationError
from flaskinventory.flaskdgraph import (UID, NewID, Predicate, Scalar,
                                        Geolocation, Variable, make_nquad, dict_to_nquad)
from flaskinventory.add.validators import InventoryValidationError
from flaskinventory.auxiliary import icu_codes
from flaskinventory.add.external import (geocode, instagram,
                                         parse_meta, siterankdata, find_sitemaps, find_feeds,
                                         build_url, twitter, facebook)
from flaskinventory import dgraph
from flask import current_app
from slugify import slugify
import secrets

import datetime


class Sanitizer:
    """ Base Class for validating data and generating mutation object
        also keeps track of user & ip address.
        Relevant return attribute are upsert_query (string), set_nquads (string), delete_nquads (string)
    """

    is_upsert = False
    upsert_query = None
    set_nquads = None
    delete_nquads = None
    edit = {}
    overwrite = {}
    newsubunits = []

    def __init__(self, user, ip):
        self.user = user
        self.user_ip = ip

    def _make_delete_nquads(self):
        # for upserts, we first have to delete all list type predicates
        # otherwise, the user cannot remove relationships, but just add to them
        del_obj = []

        for key, val in self.overwrite.items():
            for predicate in val:
                del_obj.append({'uid': key, predicate: '*'})

        nquads = [" \n ".join(dict_to_nquad(obj)) for obj in del_obj]
        return " \n ".join(nquads)

    def _parse(self):
        for item in dir(self):
            if item.startswith('parse_'):
                m = getattr(self, item)
                if callable(m):
                    m()

    def parse_unique_name(self):
        check = dgraph.get_uid('unique_name', self.data.get('unique_name'))
        if check:
            if check != str(self.edit['uid']):
                raise InventoryValidationError('Unique Name already taken!')
        self.edit['unique_name'] = self.data.get('unique_name')

    def parse_entry_review_status(self):
        if self.data.get('entry_review_status'):
            self.edit['entry_review_status'] = self.data.get(
                'entry_review_status')

    def parse_name(self):
        self.edit['name'] = self.data.get('name')

    def parse_other_names(self):
        if self.data.get('other_names'):
            if not self.edit.get('other_names'):
                self.edit['other_names'] = []

            other_names = self.data.get('other_names')
            if type(other_names) == str:
                other_names = other_names.split(',')

            self.edit['other_names'] += [item.strip()
                                         for item in other_names if item.strip() != '']

    def parse_entry_notes(self):
        if self.data.get('entry_notes'):
            self.edit['entry_notes'] = self.data.get(
                'entry_notes').strip()

    def parse_wikidata(self):
        if self.data.get('wikidataID'):
            self.edit['wikidataID'] = self.data.get('wikidataID')

    def parse_founded(self):
        if self.data.get('founded'):
            self.edit['founded'] = self.data.get('founded')

    def _resolve_geographic_name(self, query):
        geo_result = geocode(query)
        if geo_result:
            dql_string = f'''{{ q(func: eq(country_code, "{geo_result['address']['country_code']}")) @filter(type("Country")) {{ uid }} }}'''
            dql_result = dgraph.query(dql_string)
            try:
                country_uid = dql_result['q'][0]['uid']
            except Exception:
                raise InventoryValidationError(
                    f"Country not found in inventory: {geo_result['address']['country_code']}")
            geo_data = Geolocation('Point', [
                float(geo_result.get('lon')), float(geo_result.get('lat'))])

            name = None
            other_names = [query]
            if geo_result['namedetails'].get('name'):
                other_names.append(geo_result['namedetails'].get('name'))
                name = geo_result['namedetails'].get('name')

            if geo_result['namedetails'].get('name:en'):
                other_names.append(geo_result['namedetails'].get('name:en'))
                name = geo_result['namedetails'].get('name:en')

            other_names = list(set(other_names))

            if not name:
                name = query

            new_subunit = {'name': name,
                           'country': UID(country_uid),
                           'other_names': other_names,
                           'location_point': geo_data,
                           'country_code': geo_result['address']['country_code']}
            if geo_result.get('extratags'):
                if geo_result.get('extratags').get('wikidata'):
                    if geo_result.get('extratags').get('wikidata').lower().startswith('q'):
                        try:
                            new_subunit['wikidataID'] = int(geo_result.get(
                                'extratags').get('wikidata').lower().replace('q', ''))
                        except Exception as e:
                            current_app.logger.debug(
                                f'Could not parse wikidata ID in subunit: {e}')
                            pass

            return new_subunit
        else:
            return False

    def _resolve_subunit(self, subunit):
        geo_query = self._resolve_geographic_name(subunit)
        if geo_query:
            geo_query = self._add_entry_meta(geo_query, newentry=True)
            geo_query['dgraph.type'] = 'Subunit'
            geo_query['unique_name'] = f"{slugify(subunit, separator='_')}_{geo_query['country_code']}"
            # prevent duplicates
            duplicate_check = dgraph.get_uid(
                'unique_name', geo_query['unique_name'])
            if duplicate_check:
                geo_query = UID(duplicate_check)
            else:
                geo_query['uid'] = NewID(
                    f"_:{slugify(secrets.token_urlsafe(8))}")
            self.newsubunits.append(geo_query)

            return geo_query
        else:
            raise InventoryValidationError(
                f'Invalid Data! Could not resolve geographic subunit {subunit}')


class EditOrgSanitizer(Sanitizer):

    def __init__(self, data, user, ip):
        super().__init__(user, ip)
        self.is_upsert = True

        self.edit = {"uid": UID(data.get('uid')),
                     "is_person": data.get('is_person')}
        self.edit = self._add_entry_meta(self.edit)
        self.data = data

        self.overwrite = {self.edit['uid']: [
            'other_names', 'owns', 'publishes', 'country']}

        self._parse()

        nquads = dict_to_nquad(self.edit)

        self.set_nquads = " \n ".join(nquads)

        self.delete_nquads = self._make_delete_nquads()

    def _add_entry_meta(self, entry, newentry=False):
        if not newentry:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_edit_history'] = UID(self.user.uid, facets=facets)
        else:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_added'] = UID(self.user.uid, facets=facets)
            entry['entry_review_status'] = 'accepted'
            entry['creation_date'] = datetime.datetime.now(
                datetime.timezone.utc)

        return entry

    def parse_ownership_kind(self):
        self.edit['ownership_kind'] = self.data.get('ownership_kind')

    def parse_country(self):
        self.edit['country'] = UID(self.data.get('country'))

    def parse_address(self):
        if self.data.get('address_string'):
            self.edit['address_string'] = self.data.get(
                'address_string').strip()
            try:
                address_geo = geocode(self.data.get('address_string'))
                self.edit["address_geo"] = Geolocation('Point', [
                    float(address_geo.get('lon')), float(address_geo.get('lat'))])

            except:
                address_geo = None

    def parse_employees(self):
        if self.data.get('employees'):
            self.edit['employees'] = self.data.get('employees')

    def parse_owns(self):
        if self.data.get('owns'):
            org_list = self.data.get('owns')
            if type(org_list) == str:
                org_list = org_list.split(',')

            self.edit['owns'] = []

            for item in org_list:
                if item == str(self.edit['uid']):
                    continue
                if item.startswith('0x'):
                    self.edit['owns'].append(UID(item))

    def parse_publishes(self):
        if self.data.get('publishes'):
            org_list = self.data.get('publishes')
            if type(org_list) == str:
                org_list = org_list.split(',')

            self.edit['publishes'] = []

            for item in org_list:
                if item.startswith('0x'):
                    self.edit['publishes'].append(UID(item))


class EditSourceSanitizer(Sanitizer):

    def __init__(self, data, user, ip):
        super().__init__(user, ip)
        self.is_upsert = True

        self.edit = {"uid": UID(data.get('uid'))}
        self.edit = self._add_entry_meta(self.edit)
        self.data = data

        self.overwrite = {self.edit['uid']: [
            'other_names', 'related', 'country',
            'geographic_scope_subunit', 'languages', 'publication_kind',
            'topical_focus', 'publication_cycle_weekday']}

        self._parse()

        self.delete_nquads = self._make_delete_nquads()
        nquads = dict_to_nquad(self.edit)
        if len(self.newsubunits) > 0:
            for subunit in self.newsubunits:
                nquads += dict_to_nquad(subunit)

        self.set_nquads = " \n ".join(nquads)

    def _add_entry_meta(self, entry, newentry=False):
        if not newentry:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_edit_history'] = UID(self.user.uid, facets=facets)
        else:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_added'] = UID(self.user.uid, facets=facets)
            entry['entry_review_status'] = 'accepted'
            entry['creation_date'] = datetime.datetime.now(
                datetime.timezone.utc)

        return entry

    def _make_delete_nquads(self):
        # for upserts, we first have to delete all list type predicates
        # otherwise, the user cannot remove relationships, but just add to them
        del_obj = []
        if not self.upsert_query:
            self.upsert_query = ''

        for key, val in self.overwrite.items():
            for predicate in val:
                del_obj.append({'uid': key, predicate: '*'})

        related = Variable('related', 'uid')
        print(self.edit)
        self.upsert_query += f""" q_related(func: type(Source)) 
                            @filter(uid_in(related, {self.edit['uid']})) 
                            {{ {related.query()} }} """
        del_obj.append({
            'uid': related,
            'related': self.edit['uid']
        })

        nquads = [" \n ".join(dict_to_nquad(obj)) for obj in del_obj]
        return " \n ".join(nquads)

    def parse_related(self):
        if self.data.get('related'):
            src_list = self.data.get('related')
            if type(src_list) == str:
                src_list = src_list.split(',')

            self.edit['related'] = []

            for item in src_list:
                if item == str(self.edit['uid']):
                    continue
                if item.startswith('0x'):
                    self.edit['related'].append(UID(item))

    def parse_contains_ads(self):
        if self.data.get('contains_ads'):
            self.edit['contains_ads'] = self.data.get('contains_ads')

    def parse_publication_kind(self):
        if self.data.get('publication_kind'):
            if not self.edit.get('publication_kind'):
                self.edit['publication_kind'] = []

            publication_kind = self.data.get('publication_kind')
            if type(publication_kind) == str:
                publication_kind = publication_kind.split(',')

            self.edit['publication_kind'] += [item.strip()
                                              for item in publication_kind if item.strip() != '']

    def parse_special_interest(self):
        if self.data.get('special_interest'):
            self.edit['special_interest'] = self.data.get('special_interest')

    def parse_topical_focus(self):
        if self.data.get('topical_focus'):
            if not self.edit.get('topical_focus'):
                self.edit['topical_focus'] = []

            topical_focus = self.data.get('topical_focus')
            if type(topical_focus) == str:
                topical_focus = topical_focus.split(',')

            self.edit['topical_focus'] += [item.strip()
                                           for item in topical_focus if item.strip() != '']

    def parse_publication_cycle(self):
        if self.data.get('publication_cycle'):
            self.edit['publication_cycle'] = self.data.get('publication_cycle')

    def parse_publication_cycle_weekday(self):
        if self.data.get('publication_cycle_weekday'):
            if not self.edit.get('publication_cycle_weekday'):
                self.edit['publication_cycle_weekday'] = []

            publication_cycle_weekday = self.data.get(
                'publication_cycle_weekday')
            if type(publication_cycle_weekday) == str:
                publication_cycle_weekday = publication_cycle_weekday.split(
                    ',')

            self.edit['publication_cycle_weekday'] += [int(item.strip())
                                                       for item in publication_cycle_weekday if item.strip() != '']

    def parse_geographic_scope(self):
        if self.data.get('geographic_scope'):
            self.edit['geographic_scope'] = self.data.get('geographic_scope')

    def parse_geographic_scope_countries(self):
        if self.data.get('country'):
            src_list = self.data.get('country')
            if type(src_list) == str:
                src_list = src_list.split(',')

            self.edit['country'] = []

            for item in src_list:
                if item == str(self.edit['uid']):
                    continue
                if item.startswith('0x'):
                    self.edit['country'].append(UID(item))

    def parse_geographic_scope_subunit(self):
        if self.data.get('geographic_scope_subunit'):
            src_list = self.data.get('geographic_scope_subunit')
            if type(src_list) == str:
                src_list = src_list.split(',')

            self.edit['geographic_scope_subunit'] = []

            for item in src_list:
                if item == str(self.edit['uid']):
                    continue
                if item.startswith('0x'):
                    self.edit['geographic_scope_subunit'].append(UID(item))
                else:
                    geo_query = self._resolve_subunit(item)
                    if geo_query:
                        self.edit['geographic_scope_subunit'].append(
                            geo_query['uid'])

    def parse_languages(self):
        if self.data.get('languages'):
            if not self.edit.get('languages'):
                self.edit['languages'] = []

            languages = self.data.get('languages')
            if type(languages) == str:
                languages = languages.split(',')

            self.edit['languages'] += [item.strip()
                                       for item in languages if item.strip() != '']

    def parse_channel_epaper(self):
        if self.data.get('channel_epaper'):
            self.edit['channel_epaper'] = self.data.get('channel_epaper')

    def parse_payment_model(self):
        if self.data.get('payment_model'):
            self.edit['payment_model'] = self.data.get('payment_model')

    def parse_channel_url(self):
        if self.data.get('channel_url'):
            self.edit['channel_url'] = self.data.get('channel_url')

    def parse_channel_comments(self):
        if self.data.get('channel_comments'):
            self.edit['channel_comments'] = self.data.get('channel_comments')

    def parse_transcript_kind(self):
        if self.data.get('transcript_kind'):
            self.edit['transcript_kind'] = self.data.get('transcript_kind')


class EditSubunitSanitizer(Sanitizer):

    def __init__(self, data, user, ip):
        super().__init__(user, ip)
        self.is_upsert = True

        self.edit = {"uid": UID(data.get('uid'))}
        self.edit = self._add_entry_meta(self.edit)
        self.data = data

        self.overwrite = {self.edit['uid']: [
            'other_names', 'country']}

        self._parse()

        nquads = dict_to_nquad(self.edit)

        self.set_nquads = " \n ".join(nquads)

        self.delete_nquads = self._make_delete_nquads()

    def _add_entry_meta(self, entry, newentry=False):
        if not newentry:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_edit_history'] = UID(self.user.uid, facets=facets)
        else:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_added'] = UID(self.user.uid, facets=facets)
            entry['entry_review_status'] = 'accepted'
            entry['creation_date'] = datetime.datetime.now(
                datetime.timezone.utc)

        return entry

    def parse_ownership_kind(self):
        self.edit['ownership_kind'] = self.data.get('ownership_kind')

    def parse_country(self):
        self.edit['country'] = UID(self.data.get('country'))



class EditArchiveSanitizer(Sanitizer):

    def __init__(self, data, user, ip):
        super().__init__(user, ip)
        self.is_upsert = True

        self.edit = {"uid": UID(data.get('uid'))}
        self.edit = self._add_entry_meta(self.edit)
        self.data = data

        self.overwrite = {self.edit['uid']: [
            'other_names']}

        self._parse()

        nquads = dict_to_nquad(self.edit)

        self.set_nquads = " \n ".join(nquads)

        self.delete_nquads = self._make_delete_nquads()

    def _add_entry_meta(self, entry, newentry=False):
        if not newentry:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_edit_history'] = UID(self.user.uid, facets=facets)
        else:
            facets = {'timestamp': datetime.datetime.now(
                datetime.timezone.utc),
                'ip': self.user_ip}
            entry['entry_added'] = UID(self.user.uid, facets=facets)
            entry['entry_review_status'] = 'accepted'
            entry['creation_date'] = datetime.datetime.now(
                datetime.timezone.utc)

        return entry

    def parse_access(self):
        if self.data.get('access'):
            self.edit['access'] = self.data.get('access')

    def parse_description(self):
        if self.data.get('description'):
            self.edit['description'] = self.data.get('description')
    
    def parse_url(self):
        if self.data.get('url'):
            self.edit['url'] = self.data.get('url')

    def parse_sources_included(self):
        if self.data.get('sources_included'):
            src_list = self.data.get('sources_included')
            if type(src_list) == str:
                src_list = src_list.split(',')

            self.edit['sources_included'] = []

            for item in src_list:
                if item == str(self.edit['uid']):
                    continue
                if item.startswith('0x'):
                    self.edit['sources_included'].append(UID(item))


class EditDatasetSanitizer(EditArchiveSanitizer):

    def parse_sources_included(self):
        if self.data.get('sources_included'):
            src_list = self.data.get('sources_included')
            if type(src_list) == str:
                src_list = src_list.split(',')

            self.edit['sources_included'] = []

            for item in src_list:
                if item == str(self.edit['uid']):
                    continue
                if item.startswith('0x'):
                    self.edit['sources_included'].append(UID(item))
