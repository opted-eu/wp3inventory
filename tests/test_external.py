# Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.
if __name__ == "__main__" and __package__ is None:
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))
    __package__ = "examples"

from flaskinventory import create_app, dgraph
from flaskinventory.misc.forms import get_country_choices
import secrets
import unittest
from datetime import datetime
from pprint import pprint

from flaskinventory.add import external

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


class TestSanitizers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(config_json="test_config.json")
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
            cls.channel_transcript = dgraph.get_uid('unique_name', 'transcript')
            cls.channel_print = dgraph.get_uid('unique_name', 'print')

    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass
        
    def test_doi(self):
        doi = "10.1080/1461670X.2020.1745667"
        with self.app.app_context():
            publication = external.doi(doi)
            self.assertNotEqual(publication, False)
            pprint(publication)

    def test_arxiv(self):
        arxiv = "http://arxiv.org/abs/2004.02566v3"
        with self.app.app_context():
            publication = external.arxiv(arxiv)
            self.assertNotEqual(publication, False)
            pprint(publication)


if __name__ == "__main__":
    unittest.main()