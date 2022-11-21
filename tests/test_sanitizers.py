
#  Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.

if __name__ == "__main__":
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))

from pprint import pprint
from datetime import datetime
import unittest
import copy
import secrets
from flaskinventory.flaskdgraph import Schema
from flaskinventory.flaskdgraph.dgraph_types import UID, Scalar
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.main.model import Entry, Organization, Source
from flaskinventory.main.sanitizer import Sanitizer, make_sanitizer
from flaskinventory.errors import InventoryValidationError, InventoryPermissionError
from flaskinventory import create_app, dgraph
from flaskinventory.users.constants import USER_ROLES
from flaskinventory.users.dgraph import User, get_user_data
from flask_login import current_user


class Config:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = secrets.token_hex(32)
    DEBUG_MODE = False
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = None
    TWITTER_CONSUMER_KEY = None
    TWITTER_CONSUMER_SECRET = None
    TWITTER_ACCESS_TOKEN = None
    TWITTER_ACCESS_SECRET = None
    VK_TOKEN = None
    TELEGRAM_APP_ID = None
    TELEGRAM_APP_HASH = None
    TELEGRAM_BOT_TOKEN = None
    SLACK_LOGGING_ENABLED = False
    SLACK_WEBHOOK = None


class MockUser(User):
    id = '0x123'
    uid = '0x123'

    def __init__(self, user_role=USER_ROLES.Contributor):
        self.user_role = user_role


class TestSanitizers(unittest.TestCase):

    """
        Test Cases for Sanitizer classes
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(config_json="test_config.json")
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            cls.derstandard_mbh_uid = dgraph.get_uid(
                'unique_name', "derstandard_mbh")
            cls.falter_print_uid = dgraph.get_uid(
                'unique_name', 'falter_print')
            cls.derstandard_print = dgraph.get_uid(
                'unique_name', 'derstandard_print')
            cls.www_derstandard_at = dgraph.get_uid(
                'unique_name', 'www.derstandard.at')
            cls.derstandard_facebook = dgraph.get_uid(
                'unique_name', 'derstandard_facebook')
            cls.derstandard_instagram = dgraph.get_uid(
                'unique_name', 'derstandard_instagram')
            cls.derstandard_twitter = dgraph.get_uid(
                'unique_name', 'derstandard_twitter')
            cls.austria_uid = dgraph.get_uid('unique_name', 'austria')
            cls.germany_uid = dgraph.get_uid('unique_name', 'germany')
            cls.channel_website = dgraph.get_uid('unique_name', 'website')
            cls.channel_print = dgraph.get_uid('unique_name', 'print')
            cls.channel_twitter = dgraph.get_uid('unique_name', 'twitter')
            cls.channel_facebook = dgraph.get_uid('unique_name', 'facebook')
            cls.country_choices = get_country_choices()
            cls.channel_website = dgraph.get_uid('unique_name', 'website')
            cls.channel_twitter = dgraph.get_uid('unique_name', 'twitter')
            cls.channel_instagram = dgraph.get_uid('unique_name', 'instagram')
            cls.channel_vkontakte = dgraph.get_uid('unique_name', 'vkontakte')
            cls.channel_telegram = dgraph.get_uid('unique_name', 'telegram')
            cls.channel_transcript = dgraph.get_uid(
                'unique_name', 'transcript')
            cls.channel_print = dgraph.get_uid('unique_name', 'print')

    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()

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
                                    'creation_date', 'unique_name', 'name', 'other_names', 'entry_notes']

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
                self.assertGreater(len(sanitizer.entry['other_names']), 2)

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

        test_draft = {'uid': '_:newdraft',
                      'dgraph.type': 'Source',
                      'channel': {'uid': self.channel_website},
                      'name': 'https://www.schwaebische-post.de/',
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
                res = dgraph.mutation(test_draft)
                # get the UID of the mock draft
                uid = res.uids['newdraft']

            self.client.get('/logout')

        test_draft = {'uid': uid,
                      'channel': self.channel_website,
                      'channel_unique_name': 'website',
                      'name': 'https://www.schwaebische-post.de/',
                      'website_allows_comments': 'yes',
                      'website_comments_registration_required': 'no',
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
                    sanitizer = Sanitizer.edit(test_draft, dgraph_type=Source)
                
            self.client.get('/logout')

        # test if owner can edit
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():

                sanitizer = Sanitizer.edit(test_draft, dgraph_type=Source)
                self.assertIn("<entry_edit_history>", sanitizer.set_nquads)
                self.assertIn(
                    '<unique_name> "www_schwaebische_post_de"', sanitizer.set_nquads)

            self.client.get('/logout')

        # delete draft after test
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'wp3@opted.eu', 'password': 'admin123'})
            self.assertEqual(current_user.user_displayname, 'Admin')

            with self.app.app_context():
                res = dgraph.delete({'uid': uid})

            self.client.get('/logout')

    def test_new_source(self):

        mock_website = {
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

                sanitizer = Sanitizer(mock_website, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

        mock_twitter = {
            "channel": self.channel_twitter,
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
        }

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                self.assertEqual

                sanitizer = Sanitizer(mock_twitter, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

        mock_instagram = {
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

                sanitizer = Sanitizer(mock_instagram, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

        mock_telegram = {
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

                sanitizer = Sanitizer(mock_telegram, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

        mock_vk = {
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

                sanitizer = Sanitizer(mock_vk, dgraph_type=Source)
                self.assertEqual(type(sanitizer.set_nquads), str)

            self.client.get('/logout')

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
    unittest.main()
