
#  Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.

if __name__ == "__main__":
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))
    from test_setup import BasicTestSetup
    from flaskinventory import dgraph

    import unittest
    from unittest.mock import patch
    import copy
    import secrets
    import datetime
    from flaskinventory.flaskdgraph import Schema
    from flaskinventory.flaskdgraph.dgraph_types import UID, Scalar
    from flaskinventory.main.model import Entry, Organization, Source
    from flaskinventory.main.sanitizer import Sanitizer, make_sanitizer
    from flaskinventory.errors import InventoryValidationError, InventoryPermissionError
    from flaskinventory import create_app, dgraph
    from flaskinventory.users.constants import USER_ROLES
    from flaskinventory.users.dgraph import User, get_user_data
    from flask_login import current_user


class MockUser(User):
    id = '0x123'
    uid = '0x123'

    def __init__(self, user_role=USER_ROLES.Contributor):
        self.user_role = user_role

def mock_wikidata(*args):
    return {'wikidataID': 49653, 
            'other_names': [], 
            'founded': datetime.datetime(1950, 6, 5, 0, 0), 
            'address_string': 'Stuttgart', 
            'address_geo': {'type': 'Point', 
                            'coordinates': [9.1800132, 48.7784485]}}

@patch('flaskinventory.main.sanitizer.get_wikidata', mock_wikidata) 
class TestSanitizers(BasicTestSetup):

    """
        Test Cases for Sanitizer classes
    """

    def setUp(self):

        self.anon_user = MockUser(user_role=USER_ROLES.Anon)
        self.contributor = User(email="contributor@opted.eu")
        self.reviewer = User(email="reviewer@opted.eu")

        self.mock_data1 = {
            'name': 'Test',
            'other_names': 'Some, Other Name, ',
            'entry_notes': 'Some notes about the entry',
        }

        self.mock_data2 = {
            'name': 'Test Somethin',
            'other_names': ['Some', 'Other Name', ''],
            'entry_notes': 'Some notes about the entry',
        }

        self.mock1_solution_keys = ['dgraph.type', 'uid', 'entry_added', 'entry_review_status',
                                    'creation_date', 'unique_name', 'name', 'other_names', 'entry_notes', 'wikidataID']

        self.mock2_solution_keys = ['dgraph.type', 'uid', 'entry_added', 'entry_review_status',
                                    'creation_date', 'unique_name', 'name', 'other_names', 'entry_notes', 'wikidataID']

        self.mock_organization = {
            'name': 'Deutsche Bank',
            'other_names': 'TC, ',
            'wikidataID': 66048,
            'founded': 1956,
            'ownership_kind': 'private ownership',
            'country': self.country_choices[0][0],
            'address_string': 'Schwanheimer Str. 149A, 60528 Frankfurt am Main, Deutschland',
            'employees': '5000',
            'publishes': [self.falter_print_uid, self.derstandard_print],
            'owns': self.derstandard_mbh_uid,
            'party_affiliated': 'no'
        }

    def tearDown(self):
        with self.client:
            self.client.get('/logout')

    def test_new_entry(self):
        # print('-- test_new_entry() --\n')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                sanitizer = Sanitizer(self.mock_data1)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(
                    list(sanitizer.entry.keys()), self.mock1_solution_keys)
                self.assertEqual(type(sanitizer.entry['other_names']), list)

                sanitizer = Sanitizer(self.mock_data2)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(
                    list(sanitizer.entry.keys()), self.mock2_solution_keys)
                self.assertEqual(type(sanitizer.entry['other_names']), list)
                self.assertEqual(len(sanitizer.entry['other_names']), 2)

                self.assertRaises(TypeError, Sanitizer, [1, 2, 3])

            self.client.get('/logout')
            self.assertRaises(InventoryPermissionError,
                              Sanitizer, self.mock_data2)
            

    def test_list_facets(self):
        mock_data = {
            'name': 'Test',
            'other_names': 'Jay Jay,Jules,JB',
            'Jay Jay@kind': 'first',
            'Jules@kind': 'official',
            'JB@kind': 'CS-GO'
        }

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                sanitizer = Sanitizer(mock_data)
                # get rid of regular str entries
                sanitizer.entry['other_names'] = [
                    scalar for scalar in sanitizer.entry['other_names'] if not isinstance(scalar, str)]

                # assert we have all three as scalar with the correct attribute
                self.assertIsInstance(
                    sanitizer.entry['other_names'][0], Scalar)
                self.assertTrue(
                    hasattr(sanitizer.entry['other_names'][0], "facets"))
                self.assertEqual(sanitizer.entry['other_names'][0].facets, {
                                 'kind': 'first'})
                self.assertIn(
                    '<other_names> "Jay Jay" (kind="first")', sanitizer.set_nquads)

                self.assertIsInstance(
                    sanitizer.entry['other_names'][1], Scalar)
                self.assertTrue(
                    hasattr(sanitizer.entry['other_names'][1], "facets"))
                self.assertEqual(sanitizer.entry['other_names'][1].facets, {
                                 'kind': 'official'})
                self.assertIn(
                    '<other_names> "Jules" (kind="official")', sanitizer.set_nquads)

                self.assertIsInstance(
                    sanitizer.entry['other_names'][2], Scalar)
                self.assertTrue(
                    hasattr(sanitizer.entry['other_names'][2], "facets"))
                self.assertEqual(sanitizer.entry['other_names'][2].facets, {
                                 'kind': 'CS-GO'})
                self.assertIn('<other_names> "JB" (kind="CS-GO")',
                              sanitizer.set_nquads)

    def test_edit_entry(self):
        # print('-- test_edit_entry() --\n')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                # no UID
                edit_entry = {
                    'entry_review_status': 'accepted', **self.mock_data1}
                self.assertRaises(InventoryValidationError,
                                  Sanitizer.edit, edit_entry)
                self.assertRaises(InventoryValidationError,
                                  Sanitizer.edit, self.mock_data2)

                wrong_uid = {'uid': '0xfffffffff', **edit_entry}
                # wrong uid
                self.assertRaises(InventoryValidationError,
                                  Sanitizer.edit, wrong_uid)

                wrong_user = {'uid': self.derstandard_mbh_uid, **edit_entry}
                # wrong permissions
                self.assertRaises(InventoryPermissionError,
                                  Sanitizer.edit, wrong_user)

            self.client.get('/logout')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')
            with self.app.app_context():
                correct = {'uid': self.derstandard_mbh_uid, **edit_entry}
                sanitizer = Sanitizer.edit(correct)
                self.assertEqual(sanitizer.is_upsert, True)
                self.assertNotIn('dgraph.type', sanitizer.entry.keys())
                self.assertIn('entry_edit_history', sanitizer.entry.keys())
                self.assertCountEqual(
                    sanitizer.overwrite[sanitizer.entry_uid], ['other_names'])

    def test_new_org(self):
        # print('-- test_new_org() --\n')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                sanitizer = Sanitizer(
                    self.mock_organization, dgraph_type=Organization)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(sanitizer.entry['dgraph.type'], [
                                      'Entry', 'Organization'])
                self.assertEqual(
                    sanitizer.entry['entry_review_status'], 'pending')
                self.assertIsNotNone(sanitizer.set_nquads)
                self.assertIsNone(sanitizer.delete_nquads)
                # WikiDataID for Deutsche Bank
                self.assertEqual(str(sanitizer.entry['wikidataID']), '66048')
                self.assertIn('employees', sanitizer.entry.keys())

                mock_org = copy.deepcopy(self.mock_organization)
                mock_org.pop('address_string')
                sanitizer = Sanitizer(
                    self.mock_organization, dgraph_type=Organization)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(sanitizer.entry['dgraph.type'], [
                                      'Entry', 'Organization'])
                self.assertEqual(
                    sanitizer.entry['entry_review_status'], 'pending')
                self.assertIsNotNone(sanitizer.set_nquads)
                self.assertIsNone(sanitizer.delete_nquads)

    def test_edit_org(self):
        overwrite_keys = ['country', 'publishes',
                          'is_person', 'founded', 'address_string']

        mock_org_edit = {
            "uid": self.derstandard_mbh_uid,
            "name": "STANDARD Verlagsgesellschaft m.b.H.",
            "country": self.austria_uid,
            "entry_review_status": "accepted",
            "founded": "1995-04-28T00:00:00Z",
            "is_person": False,
            "unique_name": "derstandard_mbh",
            "address_string": "Vordere Zollamtsstraße 13, 1030 Wien",
            "ownership_kind": "private ownership",
            "publishes": [self.derstandard_print,
                          self.derstandard_facebook,
                          self.derstandard_instagram,
                          self.derstandard_twitter,
                          self.www_derstandard_at]
        }
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                sanitizer = Sanitizer.edit(
                    mock_org_edit, dgraph_type=Organization)
                self.assertCountEqual(
                    sanitizer.overwrite[sanitizer.entry['uid']], overwrite_keys)
                self.assertEqual(len(sanitizer.entry['publishes']), 5)

                mock_org_edit['uid'] = self.derstandard_mbh_uid
                mock_org_edit['publishes'] = " ,".join(
                    [self.derstandard_print, self.derstandard_facebook, self.derstandard_instagram, self.derstandard_twitter])
                mock_org_edit['country'] = self.germany_uid
                mock_org_edit['founded'] = '2010'
                sanitizer = Sanitizer.edit(
                    mock_org_edit, dgraph_type=Organization)
                self.assertEqual(len(sanitizer.entry['publishes']), 4)
                # self.assertEqual(type(sanitizer.entry['founded']), datetime)

    def test_draft_source(self):

        new_draft = {'uid': '_:newdraft',
                      'dgraph.type': 'Source',
                      'channel': {'uid': self.channel_print},
                      'channel_unique_name': 'print',
                      'name': 'Schwäbische Post',
                      'publication_kind': 'newspaper',
                      'geographic_scope': 'subnational',
                      'country': {'uid': self.germany_uid},
                      'languages': 'de',
                      'entry_review_status': 'draft',
                      'entry_added': {'uid': self.reviewer.uid}}

        # create a mock draft entry
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                res = dgraph.mutation(new_draft)
                # get the UID of the mock draft
                uid = res.uids['newdraft']

            self.client.get('/logout')

        edited_draft = {'uid': uid,
                      'channel': self.channel_print,
                      'channel_unique_name': 'print',
                      'name': 'Schwäbische Post',
                      'founded': '2000',
                      'publication_kind': 'newspaper',
                      'special_interest': 'no',
                      'publication_cycle': 'continuous',
                      'geographic_scope': 'subnational',
                      'country': self.germany_uid,
                      'languages': 'de',
                      'payment_model': 'partly free',
                      'contains_ads': 'non subscribers',
                      'publishes_org': self.derstandard_mbh_uid,
                      'related': [self.falter_print_uid],
                      'entry_review_status': 'pending'}

        # test if user
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                with self.assertRaises(InventoryPermissionError):
                    sanitizer = Sanitizer.edit(edited_draft, dgraph_type=Source)
                
            self.client.get('/logout')

        # test if owner can edit
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():

                sanitizer = Sanitizer.edit(edited_draft, dgraph_type=Source)
                self.assertIn("<entry_edit_history>", sanitizer.set_nquads)
                self.assertIn(
                    '<unique_name> "schwabische_post"', sanitizer.set_nquads)

            self.client.get('/logout')

        # delete draft after test
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'wp3@opted.eu', 'password': 'admin123'})
            self.assertEqual(current_user.user_displayname, 'Admin')

            with self.app.app_context():
                res = dgraph.delete({'uid': uid})

            self.client.get('/logout')

    @patch('flaskinventory.main.sanitizer.parse_meta') 
    @patch('flaskinventory.main.sanitizer.siterankdata') 
    @patch('flaskinventory.main.sanitizer.find_sitemaps') 
    @patch('flaskinventory.main.sanitizer.find_feeds') 
    def test_new_website(self, mock_find_feeds, mock_find_sitemaps, mock_siterankdata, mock_parse_meta):
        mock_parse_meta.return_value = {'names': ['Tagesthemen'], 
                                        'urls': ['https://www.tagesschau.de/']}
        mock_siterankdata.return_value = 3_000_000
        mock_find_sitemaps.return_value = ["https://www.tagesschau.de/xml/rss2/"]
        mock_find_feeds.return_value = ["https://www.tagesschau.de/rss"]

        new_website = {
            "channel_unique_name": "website",
            "channel": self.channel_website,
            "name": "https://www.tagesschau.de/",
            "other_names": "Tagesschau,Tagesthemen",
            "website_allows_comments": "no",
            "founded": "2000",
            "publication_kind": "tv show",
            "special_interest": "yes",
            "topical_focus": "politics",
            "publication_cycle": "multiple times per week",
            "publication_cycle_weekday": ["1", "2", "3", "4", "5"],
            "geographic_scope": "national",
            "country": self.germany_uid,
            "languages": "de",
            "payment_model": "free",
            "contains_ads": "no",
                            "publishes_org": [
                                "ARD",
                                self.derstandard_mbh_uid
            ],
            "publishes_person": "Caren Miosga",
            "entry_notes": "Some notes",
            "party_affiliated": "no",
            "related": [
                                "https://twitter.com/tagesschau",
                                "https://instagram.com/tagesschau",
            ],
            "newsource_https://twitter.com/tagesschau": f"{self.channel_twitter}",
            "newsource_https://instagram.com/tagesschau": f"{self.channel_instagram}",
        }

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                self.assertEqual

                sanitizer = Sanitizer(new_website, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

    @patch('flaskinventory.main.sanitizer.twitter') 
    def test_new_twitter(self, mock_twitter):

        mock_twitter.return_value = {'followers': 3_000_000, 
                                        'fullname': 'tagesschau', 
                                        'joined': datetime.date(2007, 1, 1), 
                                        'verified': True}

        new_twitter = {
            "channel": self.channel_twitter,
            "name": "@tagesschau",
            "other_names": "Tagesschau,Tagesthemen",
            "publication_kind": "tv show",
            "special_interest": "yes",
            "topical_focus": "politics",
            "publication_cycle": "continuous",
            "geographic_scope": "national",
            "country": self.germany_uid,
            "languages": "de",
            "payment_model": "free",
            "contains_ads": "no",
            "publishes_org": [
                            "ARD",
                            self.derstandard_mbh_uid
            ],
            "publishes_person": "Caren Miosga",
            "entry_notes": "Some notes",
            "party_affiliated": "no",
        }

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                self.assertEqual

                sanitizer = Sanitizer(new_twitter, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)
                mock_twitter.assert_called_with('tagesschau')

            self.client.get('/logout')

    @patch('flaskinventory.main.sanitizer.instagram') 
    def test_new_instagram(self, mock_instagram):

        mock_instagram.return_value = {'followers': 3_000_000, 
                                       'fullname': "tagesschau", 
                                       'verified': True}

        new_instagram = {
            "channel": self.channel_instagram,
            "name": "tagesschau",
            "other_names": "Tagesschau,Tagesthemen",
            "publication_kind": "tv show",
            "special_interest": "yes",
            "topical_focus": "politics",
            "publication_cycle": "continuous",
            "geographic_scope": "national",
            "country": self.germany_uid,
            "languages": "de",
            "payment_model": "free",
            "contains_ads": "no",
            "publishes_org": [
                            "ARD",
                            self.derstandard_mbh_uid
            ],
            "publishes_person": "Caren Miosga",
            "entry_notes": "Some notes",
            "party_affiliated": "no",
            "related_sources": [
                "https://twitter.com/tagesschau",
            ]
        }

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                self.assertEqual

                sanitizer = Sanitizer(new_instagram, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

    @patch('flaskinventory.main.sanitizer.telegram') 
    def test_new_telegram(self, mock_telegram):

        mock_telegram.return_value = {'followers': 1_000_000, 
                                      'fullname': "ARD_tagesschau_bot", 
                                      'joined': datetime.date(2012, 1, 1), 
                                      'verified': True, 
                                      'telegram_id': 12345678}

        new_telegram = {
            "channel": self.channel_telegram,
            "name": "ARD_tagesschau_bot",
            "other_names": "Tagesschau,Tagesthemen",
            "publication_kind": "tv show",
            "special_interest": "yes",
            "topical_focus": "politics",
            "publication_cycle": "continuous",
            "geographic_scope": "national",
            "country": self.germany_uid,
            "languages": "de",
            "payment_model": "free",
            "contains_ads": "no",
            "publishes_org": [
                            "ARD",
                            self.derstandard_mbh_uid
            ],
            "publishes_person": "Caren Miosga",
            "entry_notes": "Some notes",
            "party_affiliated": "no",
            "related_sources": [
                "https://twitter.com/tagesschau",
            ]
        }

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                self.assertEqual

                sanitizer = Sanitizer(new_telegram, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

    @patch('flaskinventory.main.sanitizer.vkontakte') 
    def test_new_vk(self, mock_vk):

        mock_vk.return_value = {'followers': 100_000, 
                                'fullname': "anonymousnews_org", 
                                'verified': False,
                                'description': 'Description text'}

        new_vk = {
            "channel": self.channel_vkontakte,
            "name": "anonymousnews_org",
            "publication_kind": "alternative media",
            "publication_cycle": "continuous",
            "geographic_scope": "multinational",
            "country": [self.germany_uid, self.austria_uid],
            "languages": "de",
            "payment_model": "free",
            "contains_ads": "no",
            "entry_notes": "Some notes",
        }

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                self.assertEqual

                sanitizer = Sanitizer(new_vk, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

    def test_new_facebook(self):

        mock_facebook = {'channel': self.channel_facebook,
                         'name': 'some_source',
                         'other_names': 'other names',
                         'founded': '2000',
                         'publication_kind': 'news agency',
                         'special_interest': 'yes',
                         'topical_focus': 'society',
                         'publication_cycle': 'multiple times per week',
                         'publication_cycle_weekday': ['1', '2', '3'],
                         'geographic_scope': 'national',
                         'country': self.germany_uid,
                         'languages': 'ak',
                         'contains_ads': 'yes',
                         'publishes_org': ['New Media'],
                         'audience_size|count': '1234444',
                         'audience_size|unit': 'likes',
                         'party_affiliated': 'no'}
        
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                self.assertEqual

                sanitizer = Sanitizer(mock_facebook, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)
                mock_facebook['geographic_scope'] = 'NA'
                self.assertRaises(InventoryValidationError, Sanitizer, mock_facebook, dgraph_type=Source)

            self.client.get('/logout')


if __name__ == "__main__":
    unittest.main(verbosity=2)
