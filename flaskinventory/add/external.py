from flask import current_app
import requests
from requests.models import PreparedRequest
import requests.exceptions
import feedparser
from urllib.robotparser import RobotFileParser
import urllib.parse
from bs4 import BeautifulSoup as bs4
import re
import json
import instaloader
import tweepy
from dateutil.parser import isoparse


def geocode(address):
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


# Sitemaps & RSS/XML/Atom Feeds


def build_url(site):
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

def test_url(site):
    site = build_url(site)
    if not site:
        return False
    try:
        r = requests.head(site, timeout=5)
    except Exception as e:
        return False
    
    if r.ok:
        return True
    
    return False


def find_sitemaps(site):
    site = build_url(site)
    if not site:
        return []

    if site.endswith('/'):
        site = site[:-1]

    r = requests.get(site)
    if r.status_code != 200:
        raise requests.RequestException(
            f'Could not reach {site}. Status: {r.status_code}')

    rp = RobotFileParser()
    rp.set_url(site + '/robots.txt')
    rp.read()
    if len(rp.sitemaps) > 0:
        return rp.sitemaps
    else:
        return []


def find_feeds(site):
    site = build_url(site)
    if not site:
        return []
    
    if site.endswith('/'):
        site = site[:-1]

    # first: naive approach
    try:
        r = requests.get(site + '/rss')
        if 'xml' in r.headers['Content-Type'] or 'rss' in r.headers['Content-Type']:
            return [site + '/rss']
    except Exception:
        pass

    r = requests.get(site)
    result = []
    possible_feeds = []
    html = bs4(r.content, 'lxml')
    feed_urls = html.find_all("link", rel="alternate")
    if len(feed_urls) > 1:
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


def parse_meta(url):

    urls = []
    names = []

    site = build_url(url)
    if not site:
        return False, False

    r = requests.get(site)

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


def opengraph(soup):
    if soup.find('meta', property='og:title'):
        title = soup.find('meta', property='og:title')['content']
    else:
        title = None

    if soup.find('meta', property='og:url'):
        url = soup.find('meta', property='og:url')['content']
    else:
        url = None

    return title, url


def schemaorg(soup):
    schemas = soup.find_all('script', type=re.compile(r'json'))
    if len(schemas) == 0:
        return False, False

    name = None
    url = None

    for item in schemas:
        parsed = json.loads(item.string)
        if parsed.get('@type'):
            if parsed.get('@type').lower() == "webpage":
                url = parsed.get('url')
                name = parsed.get('name')

    return name, url


def siterankdata(site):
    site = site.replace('http://', '').replace('https://',
                                               '').replace('www.', '')
    if site.endswith('/'):
        site = site[:-1]

    r = requests.get("https://siterankdata.com/" + site)

    if r.status_code != 200:
        return False

    soup = bs4(r.content, 'lxml')

    try:
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
        verified = None

    return {'followers': followers, 'fullname': fullname, 'verified': verified}


def generate_twitter_api():
    twitter_auth = tweepy.OAuthHandler(current_app.config["TWITTER_CONSUMER_KEY"],
                                       current_app.config["TWITTER_CONSUMER_SECRET"])
    twitter_auth.set_access_token(current_app.config["TWITTER_ACCESS_TOKEN"],
                                  current_app.config["TWITTER_ACCESS_SECRET"])

    return tweepy.API(twitter_auth)


def twitter(username):
    api = generate_twitter_api()

    user = api.get_user(username)

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
