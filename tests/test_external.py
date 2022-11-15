# Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.
if __name__ == "__main__":
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))

from flaskinventory import create_app, dgraph
from flaskinventory.misc.forms import get_country_choices
import unittest
from flaskinventory.add import external


class TestSanitizers(unittest.TestCase):

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
        pass

    def tearDown(self):
        pass

    def test_doi(self):
        doi = "10.1080/1461670X.2020.1745667"
        with self.app.app_context():
            publication = external.doi(doi)
            self.assertNotEqual(publication, False)

    def test_arxiv(self):
        arxiv = "http://arxiv.org/abs/2004.02566v3"
        with self.app.app_context():
            publication = external.arxiv(arxiv)
            self.assertNotEqual(publication, False)

    def test_cran(self):
        cran = "corpustools"
        with self.app.app_context():
            package = external.cran(cran)
            self.assertNotEqual(package, False)
            self.assertCountEqual(list(package.keys()), ['programming_languages', 'platform', 'user_access',
                                  'open_source', 'name', 'cran', 'description', 'other_names', 'github', 'url', 'license', 'authors'])
            self.assertEqual(package['programming_languages'], ['r'])

    def test_vkontakte(self):
        handle = "dieunbestechlichen"
        with self.app.app_context():
            profile = external.vkontakte(handle)
            self.assertNotEqual(profile, False)

    def test_website(self):
        website = "https://www.heise.de/"
        with self.app.app_context():
            names, urls = external.parse_meta(website)
            self.assertGreaterEqual(len(names), 1)
            self.assertGreaterEqual(len(urls), 1)
            daily_visitors = external.siterankdata(website)
            self.assertGreaterEqual(daily_visitors, 1000)
            sitemaps = external.find_sitemaps(website)
            self.assertEqual(type(sitemaps), list)
            self.assertGreaterEqual(len(sitemaps), 1)

            feeds = external.find_feeds(website)
            self.assertGreaterEqual(len(feeds), 1)

    def test_twitter(self):
        handle = "heiseonline"
        with self.app.app_context():
            profile = external.twitter(handle)
            self.assertNotEqual(profile, False)
            self.assertCountEqual(list(profile.keys()), [
                                  'followers', 'fullname', 'joined', 'verified'])
            self.assertGreaterEqual(profile['followers'], 100)

    def test_instagram(self):
        handle = "bild"
        with self.app.app_context():
            profile = external.instagram(handle)
            self.assertNotEqual(profile, False)
            self.assertCountEqual(list(profile.keys()), [
                                  'followers', 'fullname', 'verified'])
            self.assertGreaterEqual(profile['followers'], 100)

    def test_telegram(self):
        handle = "faz_net_official_bot"
        with self.app.app_context():
            profile = external.telegram(handle)
            self.assertNotEqual(profile, False)
            self.assertCountEqual(list(profile.keys()), [
                                  'followers', 'fullname', 'joined', 'verified', 'telegram_id'])

    def test_wikidata_id(self):
        olaf = "Olaf Scholz"
        with self.app.app_context():
            wikidataid = external.lookup_wikidata_id(olaf)
            self.assertEqual(wikidataid, 'Q61053')

    def test_wikidata(self):
        spd = "SPD"
        with self.app.app_context():
            wikidata = external.get_wikidata(spd)
            self.assertCountEqual(list(wikidata.keys()), [
                                  'wikidataID', 'other_names', 'founded', 'country', 'address_string', 'address_geo'])
            self.assertEqual(wikidata['wikidataID'], 49768)


if __name__ == "__main__":
    unittest.main()
