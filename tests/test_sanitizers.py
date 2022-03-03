
# Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.
if __name__ == "__main__" and __package__ is None:
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))
    __package__ = "examples"

from flask_login import current_user
from flaskinventory.users.dgraph import User, get_user_data
from flaskinventory.users.constants import USER_ROLES
from flaskinventory import create_app, dgraph
from flaskinventory.errors import InventoryValidationError, InventoryPermissionError
from flaskinventory.main.sanitizer import Sanitizer, make_sanitizer
from flaskinventory.main.model import Entry, Organization, Source
from flaskinventory.misc.forms import get_country_choices
from flaskinventory.flaskdgraph.dgraph_types import UID
from flaskinventory.flaskdgraph import Schema
import secrets
import copy
import unittest
from datetime import datetime

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

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            cls.derstandard_mbh_uid = dgraph.get_uid('unique_name', "derstandard_mbh")
            cls.falter_print_uid = dgraph.get_uid('unique_name', 'falter_print')
            cls.derstandard_print = dgraph.get_uid('unique_name', 'derstandard_print')
            cls.www_derstandard_at = dgraph.get_uid('unique_name', 'www.derstandard.at')
            cls.derstandard_facebook = dgraph.get_uid('unique_name', 'derstandard_facebook')
            cls.derstandard_instagram = dgraph.get_uid('unique_name', 'derstandard_instagram')
            cls.derstandard_twitter = dgraph.get_uid('unique_name', 'derstandard_twitter')
            cls.austria_uid = dgraph.get_uid('unique_name', 'austria')
            cls.germany_uid = dgraph.get_uid('unique_name', 'germany')
            cls.country_choices = get_country_choices()

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
        
    def test_login(self):
        # print('-- test_login() --\n')

        with self.client:
            response = self.client.post('/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')
            self.client.get('/logout')

        with self.client:
            response = self.client.post('/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')
            self.client.get('/logout')

        with self.client:
            response = self.client.post('/login', data={'email': 'wp3@opted.eu', 'password': 'admin123'})
            self.assertEqual(current_user.user_displayname, 'Admin')
            self.client.get('/logout')


    def test_new_entry(self):
        # print('-- test_new_entry() --\n')

        with self.client:
            response = self.client.post('/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')
        
            with self.app.app_context():
                sanitizer = Sanitizer(self.mock_data1)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(list(sanitizer.entry.keys()), self.mock1_solution_keys)
                self.assertEqual(type(sanitizer.entry['other_names']), set)
                self.assertGreater(len(sanitizer.entry['other_names']), 2)
            
                sanitizer = Sanitizer(self.mock_data2)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(list(sanitizer.entry.keys()), self.mock2_solution_keys)
                self.assertEqual(type(sanitizer.entry['other_names']), set)
                self.assertEqual(len(sanitizer.entry['other_names']), 2)
            
                self.assertRaises(TypeError, Sanitizer, [1, 2, 3])

            self.client.get('/logout')
            self.assertRaises(InventoryPermissionError, Sanitizer, self.mock_data2)

        

    def test_edit_entry(self):
        # print('-- test_edit_entry() --\n')
        
        with self.client:
            response = self.client.post('/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                # no UID
                edit_entry = {'entry_review_status': 'accepted', **self.mock_data1}
                self.assertRaises(InventoryValidationError, Sanitizer.edit, edit_entry)
                self.assertRaises(InventoryValidationError, Sanitizer.edit, self.mock_data2)

                wrong_uid = {'uid': '0xfffffffff', **edit_entry}
                # wrong uid
                self.assertRaises(InventoryValidationError, Sanitizer.edit, wrong_uid)

                wrong_user = {'uid': self.derstandard_mbh_uid, **edit_entry}
                # wrong permissions
                self.assertRaises(InventoryPermissionError, Sanitizer.edit, wrong_user)

            self.client.get('/logout')

        with self.client:
            response = self.client.post('/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')
            with self.app.app_context():
                correct = {'uid': self.derstandard_mbh_uid, **edit_entry}
                sanitizer = Sanitizer.edit(correct)
                self.assertEqual(sanitizer.is_upsert, True)
                self.assertNotIn('dgraph.type', sanitizer.entry.keys())
                self.assertIn('entry_edit_history', sanitizer.entry.keys())
                self.assertCountEqual(sanitizer.overwrite[sanitizer.entry['uid']], ['other_names', 'wikidataID'])

    def test_new_org(self):
        # print('-- test_new_org() --\n')

        with self.client:
            response = self.client.post('/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                sanitizer = make_sanitizer(self.mock_organization, Organization)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(sanitizer.entry['dgraph.type'], ['Entry', 'Organization'])
                self.assertEqual(sanitizer.entry['entry_review_status'], 'pending')
                self.assertIsNotNone(sanitizer.set_nquads)
                self.assertIsNone(sanitizer.delete_nquads)
                self.assertEqual(sanitizer.entry['wikidataID'], 66048) # WikiDataID for Deutsche Bank
                self.assertIn('employees', sanitizer.entry.keys())
                
                mock_org = copy.deepcopy(self.mock_organization)
                mock_org.pop('address_string')
                sanitizer = make_sanitizer(self.mock_organization, Organization)
                self.assertEqual(sanitizer.is_upsert, False)
                self.assertCountEqual(sanitizer.entry['dgraph.type'], ['Entry', 'Organization'])
                self.assertEqual(sanitizer.entry['entry_review_status'], 'pending')
                self.assertIsNotNone(sanitizer.set_nquads)
                self.assertIsNone(sanitizer.delete_nquads)

    def test_edit_org(self):
        overwrite_keys = ['other_names', 'wikidataID', 'country', 'owns', 'publishes']
        
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
            response = self.client.post('/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertEqual(current_user.user_displayname, 'Reviewer')

            with self.app.app_context():
                sanitizer = make_sanitizer(mock_org_edit, Organization, edit=True)
                self.assertEqual(type(sanitizer.entry['founded']), datetime)
                self.assertCountEqual(sanitizer.overwrite[sanitizer.entry['uid']], overwrite_keys)
                self.assertEqual(len(sanitizer.entry['publishes']), 5)

                mock_org_edit['uid'] = self.derstandard_mbh_uid
                mock_org_edit['publishes'] = " ,".join([self.derstandard_print, self.derstandard_facebook, self.derstandard_instagram, self.derstandard_twitter])
                mock_org_edit['country'] = self.germany_uid
                mock_org_edit['founded'] = '2010'
                sanitizer = make_sanitizer(mock_org_edit, Organization, edit=True)
                self.assertEqual(len(sanitizer.entry['publishes']), 4)
                self.assertEqual(type(sanitizer.entry['founded']), datetime)

    def test_new_source(self):
        with self.client:
            response = self.client.post('/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertEqual(current_user.user_displayname, 'Contributor')

            with self.app.app_context():
                Source.country.get_choices()
                Organization.country.get_choices()
                Source.published_by
                print(dir(Source.generate_new_entry_form()))


if __name__ == "__main__":
    unittest.main()