
import secrets
import unittest
from flaskinventory import create_app, dgraph
from sys import path
from os.path import dirname

path.append(dirname(path[0]))


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


class BasicTestSetup(unittest.TestCase):

    user_login = None
    logged_in = None

    @classmethod
    def setUpClass(cls):
        cls.verbatim = False
        cls.app = create_app(config_class=Config)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            cls.derstandard_mbh_uid = dgraph.get_uid(
                'unique_name', "derstandard_mbh")

            cls.organizations = [cls.derstandard_mbh_uid]

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

            cls.sources = [cls.falter_print_uid, cls.derstandard_print,
                           cls.www_derstandard_at, cls.derstandard_facebook,
                           cls.derstandard_instagram, cls.derstandard_twitter]

            cls.austria_uid = dgraph.get_uid('unique_name', 'austria')
            cls.germany_uid = dgraph.get_uid('unique_name', 'germany')
            cls.switzerland_uid = dgraph.get_uid('unique_name', 'switzerland')

            cls.countries = [cls.austria_uid,
                             cls.germany_uid, cls.switzerland_uid]

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

            cls.channels = [cls.channel_website,
                            cls.channel_print,
                            cls.channel_twitter,
                            cls.channel_facebook,
                            cls.channel_website,
                            cls.channel_twitter,
                            cls.channel_instagram,
                            cls.channel_vkontakte,
                            cls.channel_telegram,
                            cls.channel_transcript,
                            cls.channel_print]

            cls.rejected_entry = dgraph.get_uid('unique_name', 'rejected12345')

            cls.contributor_uid = dgraph.get_uid('email', 'contributor@opted.eu')
            cls.reviewer_uid = dgraph.get_uid('email', 'reviewer@opted.eu')
            cls.admin_uid = dgraph.get_uid('email', 'wp3@opted.eu')

    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass
