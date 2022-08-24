#  Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.

if __name__ == "__main__" and __package__ is None:
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))
    __package__ = "examples"

from flaskinventory.main.model import Source
from flaskinventory.flaskdgraph import Schema
from flaskinventory.view.routes import build_query_string
from flaskinventory import create_app, dgraph

from flask import request
from pprint import pprint
import unittest
import secrets


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

class TestQueries(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.verbatim = False
        cls.app = create_app(config_class=Config)
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
            cls.switzerland_uid = dgraph.get_uid('unique_name', 'switzerland')
            cls.channel_website = dgraph.get_uid('unique_name', 'website')
            cls.channel_print = dgraph.get_uid('unique_name', 'print')
            cls.channel_twitter = dgraph.get_uid('unique_name', 'twitter')
            cls.channel_facebook = dgraph.get_uid('unique_name', 'facebook')
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
        with self.client:
            response = self.client.post(
                '/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})

    def tearDown(self):
        # with self.client:
        #     self.client.get('/logout')
        pass

    def test_query_builder(self):
        if self.verbatim:
            print('-- test_query_builder() --\n')

        with self.client as c:
            # response = c.get('/query/development?languages=de&channel=0x2713&email=wp3@opted.eu')
            # pprint(response.json)
            query_string = {'languages': ['de', 'en'],
                            'channel': self.channel_print,
                            'email': "wp3@opted.eu"
                        }

            response = c.get('/query/development/json', query_string=query_string)
            req_dict = request.args.to_dict(flat=False)
            # print(req_dict)
            self.assertCountEqual(req_dict['languages'], ['en', 'de'])
            # pprint(response.json)
            response = c.get(f'/query/development?languages=de&channel={self.channel_print}&channel={self.channel_website}')
            # pprint(response.json)


    # different predicates are combined with AND operators
    # e.g., publication_kind == "newspaper" AND geographic_scope == "national"
    def test_different_predicates(self):
        if self.verbatim:
            print('-- test_different_predicates() --\n')

        with self.client as c:
            query_string = {"languages": ["de"],
                            "publication_kind": "alternative media",
                            "channel": self.channel_print}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(response.json[0]['unique_name'], "direkt_print")

            query_string = {"publication_kind": "newspaper",
                            "channel": self.channel_website,
                            "country": self.austria_uid}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(response.json[0]['unique_name'], "www.derstandard.at")

    # same Scalar predicates are combined with OR operators
    # e.g., payment_model == "free" OR payment_model == "partly free"
    def test_same_scalar_predicates(self):
        if self.verbatim:
            print('-- test_same_scalar_predicates() --\n')

        with self.client as c:
            # German that is free OR partly for free
            query_string = {"languages": ["de"],
                            "payment_model": ["free", "partly free"]
                            }

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(response.json[0]['unique_name'], "www.derstandard.at")

            # English that is free OR partly for free
            query_string = {"languages": ["en"],
                            "payment_model": ["free", "partly free"]
                            }

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(response.json[0]['unique_name'], "globalvoices_org_website")

            # Free or partly for free IN Germany, but in English
            query_string = {"languages": ["en"],    
                            "payment_model": ["free", "partly free"],
                            "country": self.germany_uid
                            }

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 0)

            # twitter OR instagram IN austria
            query_string = {"channel": [self.channel_twitter, self.channel_instagram],
                            "country": self.austria_uid
                            }

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 2)


    # same List predicates are combined with AND operators
    # e.g., languages == "en" AND languages == "de"
    def test_same_list_predicates(self):
        if self.verbatim:
            print('-- test_same_list_predicates() --\n')

        with self.client as c:
            # English AND German speaking that is either free or partly free
            query_string = {"languages": ["de", "en"],
                            "payment_model": ["free", "partly free"]
                            }

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 0)

            # English AND Hungarian speaking that is either free or partly free
            query_string = {"languages": ["en", "hu"],
                            "payment_model": ["free", "partly free"]
                            }

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(response.json[0]['unique_name'], "globalvoices_org_website")

    def test_date_predicates(self):
        if self.verbatim:
            print('-- test_date_predicates() --\n')

        with self.client as c:
            # Founded by exact year
            query_string = {"founded": ["1995"]}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 2)
            

            # Founded in range
            query_string = {"founded": ["1990", "2000"]}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 4)

            # Founded before year
            query_string = {"founded": ["2000"],
                            "founded*operator": 'lt'}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 6)

            # Founded after year
            query_string = {"founded": ["2000"],
                            "founded*operator": 'gt'}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 5)


            # self.assertEqual(len(response.json), 0)

    def test_boolean_predicates(self):
        if self.verbatim:
            print('-- test_boolean_predicates() --\n')
        with self.client as c:
            # verified social media account
            query_string = {"verified_account": True}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 3)

            query_string = {"verified_account": 'true'}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 3)

    
    def test_integer_predicates(self):
        if self.verbatim:
            print('-- test_integer_predicates() --\n')
        # No queryable integer predicate in current data model
        # with self.client as c:
        #     query_string = {"publication_cycle_weekday": 3}

        #     response = c.get(f'/query/development/json', query_string=query_string)
        #     self.assertEqual(response.json[0]['unique_name'], 'falter_print')


    def test_facet_filters(self):
        if self.verbatim:
            print('-- test_facet_filters() --\n')
        with self.client as c:
            query_string = {"audience_size|papers_sold": 52000,
                            "audience_size|papers_sold*operator": 'gt',
                            "audience_size|unit": "papers sold",
                            "audience_size|count": 52000,
                            "audience_size|count*operator": 'gt'}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(response.json[0]['unique_name'], 'derstandard_print')

            # TODO: arbitrary filtering for facets:
            # papers_sold / copies_sold / followers ????

    def test_type_filters(self):
        if self.verbatim:
            print('-- test_type_filters() --\n')
        
        with self.client as c:
            query_string = {"dgraph.type": "Source",
                            "country": self.germany_uid}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 1)

            query_string = {"dgraph.type": ["Source", "Organization"],
                            "country": self.austria_uid}

            response = c.get(f'/query/development/json', query_string=query_string)
            self.assertEqual(len(response.json), 11)


if __name__ == "__main__":
    unittest.main()
