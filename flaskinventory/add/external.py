# built in modules

from datetime import datetime
from urllib.robotparser import RobotFileParser
import urllib.parse
import re
import json
import asyncio
from typing import Union, Tuple

# external utils 
import requests
from requests.models import PreparedRequest
import requests.exceptions
from dateutil import parser as dateparser
import feedparser
from bs4 import BeautifulSoup as bs4
import instaloader
import tweepy
from telethon import TelegramClient

# flask
from flask import current_app
from dateutil.parser import isoparse

from flaskinventory import dgraph
from flaskinventory.errors import InventoryValidationError

def geocode(address: str) -> dict:
    payload = {'q': address,
               'format': 'jsonv2',
               'addressdetails': 1,
               'limit': 1,
               'namedetails': 1,
               'extratags': 1}
    api = "https://nominatim.openstreetmap.org/search"
    r = requests.get(api, params=payload)
    if r.status_code != 200:
        return False
    elif len(r.json()) == 0:
        return False
    else:
        return r.json()[0]


def reverse_geocode(lat, lon) -> dict:
    api = "https://nominatim.openstreetmap.org/reverse"
    payload = {'lat': lat, 'lon': lon, 'format': 'json'}
    r = requests.get(api, params=payload)
    if r.status_code != 200:
        return False
    elif 'display_name' not in r.json().keys():
        return False
    else:
        return r.json()

# Sitemaps & RSS/XML/Atom Feeds


def build_url(site: str):
    if not isinstance(site, str):
        site = str(site)
    if site.endswith('/'):
        site = site[:-1]
    if not site.startswith('http'):
        site = 'https://' + site
    prepared_request = PreparedRequest()
    try:
        prepared_request.prepare_url(site, None)
        return prepared_request.url
    except Exception as e:
        return False

def perform_request(site: str) -> requests.Response:

    headers = {'user-agent':
               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"}

    try:
        r = requests.get(site, headers=headers)
    except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
        try:
            r = requests.get(site, verify=False, headers=headers)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError):
            try:
                r = requests.get(site.replace('https', 'http'), verify=False, headers=headers)
            except Exception as e:
                current_app.logger.error(f'Error when requesting {site}: {e}')
                raise InventoryValidationError(
                    f'''Could not verify this address exists: {site}.\n
                        Please make sure the entered address is correct (e.g. starts with "https://") 
                        and also make sure the website exists.\n
                        If the issue persists please contact us.\n
                        Error message: {e}
                        '''
                    )
    return r or False

def test_url(site):
    site = build_url(site)
    if not site:
        return False
    r = perform_request(site)

    if not r:
        return False

    if r.ok:
        return True

    return False


def find_sitemaps(site: str) -> list:
    site = build_url(site)
    if not site:
        return []

    if site.endswith('/'):
        site = site[:-1]

    r = perform_request(site)
    if not r:
        return []

    if r.status_code != 200:
        raise requests.RequestException(
            f'Could not reach {site}. Status: {r.status_code}')
    try:
        rp = RobotFileParser()
        rp.set_url(site + '/robots.txt')
        rp.read()
        if len(rp.sitemaps) > 0:
            return rp.sitemaps
        else:
            return []
    except Exception as e:
        current_app.logger.warning(f'Could not get sitemap from {site}: {e}')
        return []


def find_feeds(site: str) -> list:
    site = build_url(site)
    if not site:
        return []

    if site.endswith('/'):
        site = site[:-1]

    headers = {"user-agent":
               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"}

    # first: naive approach
    try:
        r = requests.get(site + '/rss', headers=headers, verify=False)
        if 'xml' in r.headers['Content-Type'] or 'rss' in r.headers['Content-Type']:
            return [site + '/rss']
    except requests.exceptions.SSLError:
        site = site.replace('https', 'http')
        r = requests.get(site, verify=False)
    except Exception:
        pass

    r = perform_request(site)
    if not r:
        return []

    result = []
    possible_feeds = []
    html = bs4(r.content, 'lxml')
    feed_urls = html.find_all("link", rel="alternate")
    if len(feed_urls) > 0:
        for f in feed_urls:
            t = f.get("type")
            if t:
                if "rss" in t or "xml" in t:
                    href = f.get("href")
                    if href:
                        possible_feeds.append(href)
    parsed_url = urllib.parse.urlparse(site)
    base = parsed_url.scheme + "://" + parsed_url.hostname
    atags = html.find_all("a")
    for a in atags:
        href = a.get("href")
        if href:
            if "xml" in href or "rss" in href or "feed" in href:
                possible_feeds.append(href)
    for url in list(set(possible_feeds)):
        parsed_feed_url = urllib.parse.urlparse(url)
        if parsed_feed_url.scheme == '':
            scheme = 'https'
        else:
            scheme = parsed_feed_url.scheme
        if parsed_feed_url.netloc == '':
            netloc = parsed_url.hostname
        else:
            netloc = parsed_feed_url.netloc
        feed_url = scheme + '://' + netloc + parsed_feed_url.path
        f = feedparser.parse(feed_url)
        if len(f.entries) > 0:
            if feed_url not in result:
                result.append(feed_url)
    return result


def parse_meta(url: str) -> Tuple[list, list]:

    urls = []
    names = []

    site = build_url(url)
    if not site:
        return False, False

    r = perform_request(site)

    if not r:
        return False, False

    if not r.ok:
        return False, False

    soup = bs4(r.content, 'lxml')

    ogtitle, ogurl = opengraph(soup)
    schema_name, schema_url = schemaorg(soup)

    if ogtitle:
        names.append(ogtitle)

    if schema_name:
        names.append(schema_name)

    if ogurl:
        urls.append(ogurl)

    if schema_url:
        urls.append(schema_url)

    return list(set(names)), list(set(urls))


def opengraph(soup: str) -> Tuple[str, str]:
    if soup.find('meta', property='og:title'):
        title = soup.find('meta', property='og:title')['content']
    else:
        title = None

    if soup.find('meta', property='og:url'):
        url = soup.find('meta', property='og:url')['content']
    else:
        url = None

    return title, url


def schemaorg(soup: str) -> Tuple[str, str]:
    schemas = soup.find_all('script', type=re.compile(r'json'))
    if len(schemas) == 0:
        return False, False

    name = None
    url = None

    for item in schemas:
        try:
            parsed = json.loads(item.string.replace('&q;', '"'))
            if parsed.get('@type'):
                if parsed.get('@type').lower() == "webpage":
                    url = parsed.get('url')
                    name = parsed.get('name')
        except Exception as e:
            current_app.logger.debug(f'Could not parse json schema.org: {e}')
            continue

    return name, url


def siterankdata(site: str) -> Union[int, bool]:
    if not isinstance(site, str):
        site = str(site)
    site = site.replace('http://', '').replace('https://',
                                               '').replace('www.', '')
    if site.endswith('/'):
        site = site[:-1]

    current_app.logger.debug(f'requesting: {"https://siterankdata.com/" + site}')
    r = requests.get("https://siterankdata.com/" + site, timeout=30)

    if r.status_code != 200:
        current_app.logger.debug(f'Getting siterankdata failed! Status code: {r.status_code}')
        return False

    current_app.logger.debug('Succeeded in grabbing siterankdata! Now parsing...')

    try:
        soup = bs4(r.content, 'lxml')
        visitor_string = soup.find(text=re.compile('Daily Unique Visitors'))
        visitors = visitor_string.parent.parent.h3.getText(strip=True)
        visitors = int(visitors.replace(',', ''))
        return visitors

    except:
        return False


def instagram(username):

    L = instaloader.Instaloader()

    try:
        profile = instaloader.Profile.from_username(
            L.context, username.lower())
    except:
        return False

    try:
        followers = profile.followers
    except KeyError:
        followers = None

    try:
        fullname = profile.full_name
    except KeyError:
        fullname = None

    try:
        verified = profile.is_verified
    except:
        verified = False

    return {'followers': followers, 'fullname': fullname, 'verified': verified}


def generate_twitter_api():
    twitter_auth = tweepy.OAuthHandler(current_app.config["TWITTER_CONSUMER_KEY"],
                                       current_app.config["TWITTER_CONSUMER_SECRET"])
    twitter_auth.set_access_token(current_app.config["TWITTER_ACCESS_TOKEN"],
                                  current_app.config["TWITTER_ACCESS_SECRET"])

    return tweepy.API(twitter_auth)


def twitter(username):
    api = generate_twitter_api()

    user = api.get_user(screen_name=username)

    return {'followers': user.followers_count, 'fullname': user.screen_name, 'joined': user.created_at, 'verified': user.verified}


def facebook(username):
    r = requests.get('https://www.facebook.com/' + username)

    if r.status_code != 200:
        return False

    soup = bs4(r.content, 'lxml')

    for script in soup.find_all('script', type=re.compile('json')):
        if 'interactionStatistic' in script.string:
            if 'ProfilePage' in script.string:
                meta = json.loads(script.string)
                break

    profile = {}

    if meta:
        profile['fullname'] = meta.get('author').get('name')
        profile['joined'] = meta.get('author').get('foundingDate')
        try:
            profile['joined'] = isoparse(profile['joined'])
        except:
            profile['joined'] = None
        profile['followers'] = meta.get('interactionStatistic')[
            0].get('userInteractionCount')
        return profile
    else:
        return None


def lookup_wikidata_id(query):

    api = 'https://www.wikidata.org/w/api.php'

    params = {'action': 'wbsearchentities',
              'search': query, 'format': 'json', 'language': 'en'}

    result = {}

    try:
        r = requests.get(api, params=params)
        get_id = r.json()
        wikidataid = get_id['search'][0]['id']
        return wikidataid
    except:
        return False


def fetch_wikidata(wikidataid, query=None):
    from flaskinventory.flaskdgraph.dgraph_types import UID, GeoScalar
    api = 'https://www.wikidata.org/w/api.php'
    result = {'wikidataID': int(wikidataid.replace('Q', ''))}
    try:
        params = {'action': 'wbgetentities', 'languages': 'en',
                  'ids': wikidataid, 'format': 'json'}
        r = requests.get(api, params=params)
        wikidata = r.json()
    except:
        return result

    result['other_names'] = []
    try:
        aliases = wikidata['entities'][wikidataid]['aliases']['en']
        for alias in aliases:
            result['other_names'].append(alias['value'])
    except Exception as e:
        current_app.logger.debug(
            f"Could not get other names: {e}. Query: {query}. Wikidata ID: {wikidataid}")

    # P17: country, P571: inception, P1128: employees, P159: headquarters

    try:
        inception = wikidata['entities'][wikidataid]['claims']['P571'][0]['mainsnak']['datavalue']['value']['time'].replace(
            '+', '')
        if re.match(r'\d{4}-00-00', inception):
            year = re.match(r'\d{4}-00-00', inception)[0].replace('-00-00', '')
            result['founded'] = datetime(year=int(year), month=1, day=1)
        else:
            result['founded'] = isoparse(inception)
    except Exception as e:
        current_app.logger.debug(
            f"Could not get inception date: {e}. Query: {query}. Wikidata ID: {wikidataid}")

    try:
        country = wikidata['entities'][wikidataid]['claims']['P17'][0]['mainsnak']['datavalue']['value']['id'].replace(
            'Q', '')
        query_string = f'''{{q(func: eq(wikidataID, {country})) {{ name uid }} }}'''
        country_uid = dgraph.query(query_string)

        country_uid = country_uid['q'][0]['uid']
        result['country'] = UID(country_uid)
    except Exception as e:
        current_app.logger.debug(
            f"Could not get country: {e}. Query: {query}. Wikidata ID: {wikidataid}")

    try:
        result['employees'] = wikidata['entities'][wikidataid]['claims']['P1128'][
            0]['mainsnak']['datavalue']['value']['amount'].replace('+', '')
    except Exception as e:
        current_app.logger.debug(
            f"Could not get employee count: {e}. Query: {query}. Wikidata ID: {wikidataid}")

    try:
        headquarters = wikidata['entities'][wikidataid]['claims']['P159'][0]['mainsnak']['datavalue']['value']['id']
        params = {'action': 'wbgetentities', 'languages': 'en',
                  'ids': headquarters, 'format': 'json', 'props': 'labels'}
        r = requests.get(api, params=params)
        wikidata = r.json()
        address = wikidata['entities'][headquarters]['labels']['en']['value']
        geo_result = geocode(address)
        address_geo = GeoScalar('Point', [
            float(geo_result.get('lon')), float(geo_result.get('lat'))])

        result['address_string'] = address
        result['address_geo'] = address_geo
    except Exception as e:
        current_app.logger.debug(
            f"Could not get address: {e}. Query: {query}. Wikidata ID: {wikidataid}")

    return result


def get_wikidata(query):

    wikidataid = lookup_wikidata_id(query)

    if not wikidataid:
        return False

    return fetch_wikidata(wikidataid, query=query)


def vkontakte(screen_name):
    params = {
        "group_id": screen_name,
        "access_token": current_app.config["VK_TOKEN"],
        "v": "5.131",
        "fields": "id,name,screen_name,is_closed,type,description,site,verified,members_count"
    }
    api = "https://api.vk.com/method/"
    r = requests.get(api + "groups.getById", params=params)
    if r.status_code != 200:
        return False
    res = r.json()

    if "response" not in res.keys():
        return False

    res = res.get('response')
    if len(res) == 0 or type(res) is not list:
        return False

    res = res[0]

    if 'id' not in res.keys():
        return False

    return {'followers': res.get('members_count'), 'fullname': res.get('name'), 'verified': res.get('verified', False), 'description': res.get('description')}


def telegram(username):

    async def get_profile(username):
        bot = await TelegramClient('bot', current_app.config['TELEGRAM_APP_ID'], current_app.config['TELEGRAM_APP_HASH']).start(
            bot_token=current_app.config['TELEGRAM_BOT_TOKEN'])
        try:
            profile = await bot.get_entity(username)
        except ValueError as e:
            profile = False
            try: 
                profile = await bot.get_entity(username + '_bot')
            except ValueError as e:
                profile = False

        await bot.disconnect()
        return profile

    profile = asyncio.new_event_loop().run_until_complete(get_profile(username))
    if not hasattr(profile, 'to_dict') or profile == False:
        return False
    profile = profile.to_dict()
    telegram_id = profile.get('id')
    fullname = profile.get('first_name')
    joined = profile.get('date')
    verified = profile.get('verified', False)
    followers = None

    if profile['_'] == 'Channel':
        api = "https://api.telegram.org/bot"
        params = {'chat_id': '@' + username}
        r = requests.get(
            api + current_app.config['TELEGRAM_BOT_TOKEN'] + '/getChatMemberCount', params=params)
        try:
            followers = r.json().get('result')
        except:
            followers = None
        fullname = profile.get('title')

    return {'followers': followers, 'fullname': fullname, 'joined': joined, 'verified': verified, 'telegram_id': telegram_id}



def doi(doi: str) -> Union[dict, bool]:
    # clean input string
    doi = doi.replace("https://doi.org/", "")
    doi = doi.replace("http://doi.org/", "")
    doi = doi.replace("doi.org/", "")

    from flaskinventory.flaskdgraph.dgraph_types import Scalar

    api = 'https://api.crossref.org/works/'

    r = requests.get(api + doi)

    if r.status_code != 200:
        return False

    publication = r.json()

    if publication['status'] != 'ok':
        return False

    publication = publication['message']

    result = {'doi': doi}

    result['journal'] = publication.get('container-title')
    if isinstance(result['journal'], list):
        result['journal'] = result['journal'][0]
    result['title'] = publication.get('title')

    if isinstance(result['title'], list):
        result['title'] = result['title'][0]

    result['paper_kind'] = publication.get('type')

    if publication.get('created'):
        result['published_date'] = dateparser.parse(publication['created']['date-time'])

    if publication.get('link'):
        result['url'] = publication['link'][0]['URL']

    if publication.get('author'):
        authors = []
        for i, author in enumerate(publication['author']):
            author_name = f"{author.get('family', '')}, {author.get('given')}"
            authors.append(Scalar(author_name, facets={'sequence': i}))

        result['authors'] = authors

    
    return result


def arxiv(arxiv: str) -> Union[dict, bool]:
    from flaskinventory.flaskdgraph.dgraph_types import Scalar

    # clean input string
    arxiv = arxiv.replace('https://arxiv.org/abs/', '')
    arxiv = arxiv.replace('http://arxiv.org/abs/', '')
    arxiv = arxiv.replace('arxiv.org/abs/', '')
    arxiv = arxiv.replace('abs/', '')

    api = "http://export.arxiv.org/api/query"

    r = requests.get(api, params={'id_list': arxiv})

    if r.status_code != 200:
        return False

    soup = bs4(r.content, 'lxml')

    try:
        total_results = soup.find('opensearch:totalresults').text
    except:
        try:
            total_results = soup.find('opensearch:totalResults').text
        except:
            return False
    
    if int(total_results) < 1:
        return False

    result = {'arxiv': arxiv}

    try:
        result['arxiv'] = soup.entry.id.get_text()
    except:
        return False

    try:
        result['title'] = soup.entry.title.get_text().replace('\n', ' ')
    except:
        return False

    authors = []
    try:
        for i, author_tag in enumerate(soup.entry.find_all('author')):
            author = author_tag.find('name').text
            author = author.split(" ")[-1] + ', ' + " ".join(author.split(" ")[0:-1])
            authors.append(Scalar(author, facets={'sequence': i}))
    except Exception as e:
        current_app.logger.warning(f'Could not parse authors in ArXiv: {arxiv}')

    result['authors'] = authors

    try:
        result['published_date'] = dateparser.parse(soup.entry.published.text)
    except Exception as e:
        current_app.logger.warning(f'Could not parse publication date in ArXiv: {arxiv}')

    try:
        result['description'] = soup.entry.summary.get_text(strip=True).replace('\n', ' ')
    except Exception as e:
        current_app.logger.warning(f'Could not parse abstract in ArXiv: {arxiv}')

    return result


def cran(pkg) -> Union[dict, bool]:

    api = 'https://crandb.r-pkg.org/'

    r = requests.get(api + pkg)

    if r.status_code != 200:
        return False

    if not 'json' in r.headers['Content-Type']:
        return False

    data = r.json()

    result = {'programming_languages': ['r'],
                'platform': ['windows','linux','macos'],
                'user_access': 'free',
                'open_source': 'yes'}

    if 'Package' in data.keys():
        result['name'] = data['Package']

    if 'Description' in data.keys():
        result['description'] = data['Description']

    if 'Title' in data.keys():
        result['other_names'] = data['Title']

    if 'URL' in data.keys():
        result['url'] = data['URL']

    if 'License' in data.keys():
        result['license'] = data['License']

    # try extracting Author information

    authors = []
    if "Authors@R" in data.keys():
        authors_r = data['Authors@R'].split('person')
        for a in authors_r[1:]:
            mtch = re.findall(r'[\"\'](.*?)[\"\']', a)
            author = [mtch[1], mtch[0]] if len(mtch) > 1 else [mtch[0]]
            authors.append(", ".join(author))
    elif "Author" in data.keys():
        authors_raw = data['Author']
        authors_raw = re.sub(r"\[.*?\]", "", authors_raw)
        authors_raw = re.sub(r"\(.*?\)", "", authors_raw)
        authors_raw = authors_raw.replace("\n", " ")
        if ' and ' in authors_raw:
            authors_split = authors_raw.split("and")
        else:
            authors_split = authors_raw.split(',')
        authors = [a.strip() for a in authors_split]

    if len(authors) > 0:
        result['authors'] = ";".join(authors)

    return result