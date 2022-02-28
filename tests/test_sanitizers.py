
# Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.
if __name__ == "__main__" and __package__ is None:
    from sys import path
    from os.path import dirname as dir

    path.append(dir(path[0]))
    __package__ = "examples"

from flaskinventory.users.dgraph import User
from flaskinventory.users.constants import USER_ROLES
from flaskinventory import create_app, dgraph
from flaskinventory.errors import InventoryValidationError, InventoryPermissionError
from flaskinventory.main.sanitizer import OrganizationSanitizer, Sanitizer
# from flaskinventory.flaskdgraph import NewID, UID
from flaskinventory.misc.forms import get_country_choices
import secrets
import copy
import unittest

class Config:
    TESTING = True
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

        with cls.app.app_context():
            cls.derstandard_mbh_uid = dgraph.get_uid('unique_name', "derstandard_mbh")
            cls.falter_print_uid = dgraph.get_uid('unique_name', 'falter_print')
            cls.derstandard_print = dgraph.get_uid('unique_name', 'derstandard_print')
            cls.country_choices = get_country_choices()

    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()

    def setUp(self):
        self.ip = '192.168.0.1'
        self.anon_user = MockUser(user_role=USER_ROLES.Anon)
        self.contributor = MockUser()
        self.reviewer = MockUser(user_role=USER_ROLES.Reviewer)

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
        del(self.mock_organization)
        

    def test_new_entry(self):
        
        with self.app.app_context():
            sanitizer = Sanitizer(self.mock_data1, self.reviewer, self.ip)
            self.assertEqual(sanitizer.is_upsert, False)
            self.assertCountEqual(list(sanitizer.entry.keys()), self.mock1_solution_keys)
            self.assertEqual(type(sanitizer.entry['other_names']), set)
            self.assertGreater(len(sanitizer.entry['other_names']), 2)
        
        with self.app.app_context():
            sanitizer = Sanitizer(self.mock_data2, self.contributor, self.ip)
            self.assertEqual(sanitizer.is_upsert, False)
            self.assertCountEqual(list(sanitizer.entry.keys()), self.mock2_solution_keys)
            self.assertEqual(type(sanitizer.entry['other_names']), set)
            self.assertEqual(len(sanitizer.entry['other_names']), 2)
        
        with self.app.app_context():
            self.assertRaises(InventoryPermissionError, Sanitizer, self.mock_data2, self.anon_user, self.ip)

        with self.app.app_context():
            self.assertRaises(TypeError, Sanitizer, [1, 2, 3], self.contributor, self.ip)
            self.assertRaises(TypeError, Sanitizer, self.mock_data1, 'User', self.ip)
            self.assertRaises(TypeError, Sanitizer, self.mock_data1, self.contributor, 123)
        

    def test_edit_entry(self):
        
        edit_entry = {'entry_review_status': 'accepted', **self.mock_data1}
        with self.app.app_context():
            # no UID
            self.assertRaises(InventoryValidationError, Sanitizer.edit, edit_entry, self.contributor, self.ip)
            self.assertRaises(InventoryValidationError, Sanitizer.edit, self.mock_data2, self.contributor, self.ip)

        wrong_uid = {'uid': '0xfffffffff', **edit_entry}
        with self.app.app_context():
            # wrong uid
            self.assertRaises(InventoryValidationError, Sanitizer.edit, wrong_uid, self.contributor, self.ip)

        wrong_user = {'uid': self.derstandard_mbh_uid, **edit_entry}
        with self.app.app_context():
            # wrong permissions
            self.assertRaises(InventoryPermissionError, Sanitizer.edit, wrong_user, self.contributor, self.ip)

        correct = {'uid': self.derstandard_mbh_uid, **edit_entry}
        with self.app.app_context():
            sanitizer = Sanitizer.edit(correct, self.reviewer, self.ip)
            self.assertEqual(sanitizer.is_upsert, True)
            self.assertNotIn('dgraph.type', sanitizer.entry.keys())
            self.assertIn('entry_edit_history', sanitizer.entry.keys())
            self.assertCountEqual(sanitizer.overwrite[sanitizer.entry['uid']], ['other_names', 'wikidataID'])

    def test_new_org(self):

        with self.app.app_context():
            sanitizer = OrganizationSanitizer(self.mock_organization, self.contributor, self.ip)
            self.assertEqual(sanitizer.is_upsert, False)
            self.assertCountEqual(sanitizer.entry['dgraph.type'], ['Entry', 'Organization'])
            self.assertEqual(sanitizer.entry['entry_review_status'], 'pending')
            self.assertIsNotNone(sanitizer.set_nquads)
            self.assertIsNone(sanitizer.delete_nquads)
            self.assertEqual(sanitizer.entry['wikidataID'], 66048) # WikiDataID for Deutsche Bank
            self.assertIn('employees', sanitizer.entry.keys())
            
        mock_org = copy.deepcopy(self.mock_organization)
        mock_org.pop('address_string')
        with self.app.app_context():
            sanitizer = OrganizationSanitizer(mock_org, self.contributor, self.ip)
            self.assertEqual(sanitizer.is_upsert, False)
            self.assertCountEqual(sanitizer.entry['dgraph.type'], ['Entry', 'Organization'])
            self.assertEqual(sanitizer.entry['entry_review_status'], 'pending')
            self.assertIsNotNone(sanitizer.set_nquads)
            self.assertIsNone(sanitizer.delete_nquads)

    def test_edit_org(self):
        overwrite_keys = ['other_names', 'wikidataID', 'country', 'owns', 'publishes']
        pass

if __name__ == "__main__":
    unittest.main()