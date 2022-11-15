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
            assert response.status_code == 302
            assert "profile" in response.location

    def tearDown(self):
        with self.client:
            self.client.get('/logout')

    def test_query_builder(self):
        query = {'languages': ['de'],
                 'channel': [self.channel_print],
                 'email': ["wp3@opted.eu"],
                 }

        query_string = build_query_string(query)
        res = dgraph.query(query_string)
        self.assertEqual(res['total'][0]['count'], 3)

        query = {'languages': ['de', 'en'],
                 'languages*connector': ['OR'],
                 'channel': [self.channel_website],
                 }

        query_string = build_query_string(query)
        res = dgraph.query(query_string)
        self.assertEqual(res['total'][0]['count'], 2)

        query = {'country': [self.austria_uid, self.germany_uid],
                 'country*connector': ['AND'],
                 }

        query_string = build_query_string(query)
        res = dgraph.query(query_string)
        self.assertEqual(res['total'][0]['count'], 1)

        query = {'country': [self.switzerland_uid, self.germany_uid],
                 'country*connector': ['OR'],
                 }

        query_string = build_query_string(query)
        res = dgraph.query(query_string)
        self.assertEqual(res['total'][0]['count'], 1)

        query = {'dgraph.type': ['ResearchPaper'],
                 'published_date': [2010],
                 'published_date*operator': ['gt']
                 }

        query_string = build_query_string(query)
        res = dgraph.query(query_string)
        self.assertEqual(res['total'][0]['count'], 1)

        query = {'dgraph.type': ['Source'],
                 'audience_size|count': [300000],
                 'audience_size|count*operator': ['lt']
                 }

        query_string = build_query_string(query)
        res = dgraph.query(query_string)
        self.assertEqual(res['total'][0]['count'], 4)

    def test_query_route_post(self):
        if self.verbatim:
            print('-- test_query_route() --\n')

        with self.client as c:
            query = {'languages': ['de', 'en'],
                     'languages*connector': ['OR'],
                     'channel': self.channel_print,
                     'email': "wp3@opted.eu",
                     'json': True
                     }

            response = c.post('/query', data=query,
                              follow_redirects=True)

            self.assertEqual(response.json['_total_results'], 3)

    def test_private_predicates(self):
        if self.verbatim:
            print('-- test_private_predicates() --\n')

        with self.client as c:
            query = {'email': "wp3@opted.eu",
                     'json': True
                     }

            response = c.post('/query', data=query,
                              follow_redirects=True)

            self.assertEqual(response.json['_total_results'], 0)

            query = {'user_displayname': "Contributor",
                     'json': True
                     }

            response = c.post('/query', data=query,
                              follow_redirects=True)

            self.assertEqual(response.json['_total_results'], 0)

    def test_different_predicates(self):
        if self.verbatim:
            print('-- test_different_predicates() --\n')

        with self.client as c:
            query = {"languages": ["de"],
                     "publication_kind": "alternative media",
                     "channel": self.channel_print,
                     'json': True}

            response = c.get('/query',
                             query_string=query)

            self.assertEqual(response.json['result'][0]['unique_name'], "direkt_print")

            query = {"publication_kind": "newspaper",
                     "channel": self.channel_website,
                     "country": self.austria_uid,
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(
                response.json['result'][0]['unique_name'], "www.derstandard.at")

    def test_same_scalar_predicates(self):
    # same Scalar predicates are combined with OR operators
    # e.g., payment_model == "free" OR payment_model == "partly free"
        if self.verbatim:
            print('-- test_same_scalar_predicates() --\n')

        with self.client as c:
            # German that is free OR partly for free
            query = {"languages": ["de"],
                     "payment_model": ["free", "partly free"],
                     "json": True
                     }

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(
                response.json['result'][0]['unique_name'], "www.derstandard.at")

            # English that is free OR partly for free
            query = {"languages": ["en"],
                     "payment_model": ["free", "partly free"],
                     "json": True
                     }

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(
                response.json['result'][0]['unique_name'], "globalvoices_org_website")

            # Free or partly for free IN Germany, but in English
            query = {"languages": ["en"],
                     "payment_model": ["free", "partly free"],
                     "country": self.germany_uid,
                     "json": True
                     }

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 0)

            # twitter OR instagram IN austria
            query = {"channel": [self.channel_twitter, self.channel_instagram],
                     "country": self.austria_uid,
                     "json": True
                     }

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 2)

    def test_same_list_predicates(self):
    # same List predicates are combined with AND operators
    # e.g., languages == "en" AND languages == "de"
        if self.verbatim:
            print('-- test_same_list_predicates() --\n')

        with self.client as c:
            # English AND German speaking that is either free or partly free
            query = {"languages": ["de", "en"],
                     "payment_model": ["free", "partly free"],
                     "json": True
                     }

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 0)

            # English AND Hungarian speaking that is either free or partly free
            query = {"languages": ["en", "hu"],
                     "payment_model": ["free", "partly free"],
                     "json": True
                     }

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(
                response.json['result'][0]['unique_name'], "globalvoices_org_website")

    def test_date_predicates(self):
        if self.verbatim:
            print('-- test_date_predicates() --\n')

        with self.client as c:
            # Founded by exact year
            query = {"founded": ["1995"],
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 2)

            # Founded in range
            query = {"founded": ["1990", "2000"],
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 4)

            # Founded before year
            query = {"founded": ["2000"],
                     "founded*operator": 'lt',
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 6)

            # Founded after year
            query = {"founded": ["2000"],
                     "founded*operator": 'gt',
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 5)

            # self.assertEqual(len(response.json['result']), 0)

    def test_boolean_predicates(self):
        if self.verbatim:
            print('-- test_boolean_predicates() --\n')
        with self.client as c:
            # verified social media account
            query = {"verified_account": True,
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 3)

            query = {"verified_account": 'true',
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 3)

    def test_integer_predicates(self):
        if self.verbatim:
            print('-- test_integer_predicates() --\n')
        # No queryable integer predicate in current data model
        # with self.client as c:
        #     query = {"publication_cycle_weekday": 3}

        #     response = c.get('/query', query_string=query)
        #     self.assertEqual(response.json['result'][0]['unique_name'], 'falter_print')

    def test_facet_filters(self):
        if self.verbatim:
            print('-- test_facet_filters() --\n')
        with self.client as c:
            query = {"audience_size|unit": "copies sold",
                     "audience_size|count": 52000,
                     "audience_size|count*operator": 'gt',
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            print(response.json)
            self.assertEqual(
                response.json['result'][0]['unique_name'], 'derstandard_print')


    def test_type_filters(self):
        if self.verbatim:
            print('-- test_type_filters() --\n')

        with self.client as c:
            query = {"dgraph.type": "Source",
                     "country": self.germany_uid,
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 1)

            query = {"dgraph.type": ["Source", "Organization"],
                     "country": self.austria_uid,
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(len(response.json['result']), 11)


if __name__ == "__main__":
    unittest.main()
