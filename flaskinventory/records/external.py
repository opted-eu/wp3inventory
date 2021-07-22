from os import name
import time
import requests
import feedparser
from urllib.robotparser import RobotFileParser
import urllib.parse
from bs4 import BeautifulSoup as bs4
import re
import json
from requests.api import head
import validators

def geocode(address):
    payload = {'q': address, 
        'format': 'jsonv2', 
        'addressdetails': 1, 
        'limit': 1, 
        'namedetails': 1}
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
    if site.startswith('http'):
        validators.url(site)
    else:
        # domain validator needs improvement
        validators.domain(site)
        site = 'https://' + site
    return site


def find_sitemaps(site):
    if site.endswith('/'):
        site = site[:-1]
    if site.startswith('http'):
        validators.url(site)
    else:        
        site = 'https://' + site
    
    r = requests.get(site)
    if r.status_code != 200:
        raise requests.RequestException(f'Could not reach {site}. Status: {r.status_code}')

    rp = RobotFileParser()
    rp.set_url(site + '/robots.txt')
    rp.read()
    if len(rp.sitemaps) > 0:
        return rp.sitemaps
    else:
        return []


def find_feeds(site):
    site = build_url(site)

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
        else: scheme = parsed_feed_url.scheme
        if parsed_feed_url.netloc == '':
            netloc = parsed_url.hostname
        else: netloc = parsed_feed_url.netloc
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

    r = requests.get(site)

    if r.status_code != 200:
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
        return False
    
    name = None
    url = None
    
    for item in schemas:
        parsed = json.loads(item.string)
        if parsed.get('@type').lower() == "webpage":
            url = parsed.get('url')
            name = parsed.get('name')

    return name, url

def siterankdata(site):
    site = site.replace('http://', '').replace('https://', '').replace('www.', '')
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
    headers = {'User-Agent': 'Mozilla'}

    url = "https://www.instagram.com/"

    r = requests.get(url + username.lower() + '/?__a=1', headers=headers)

    if r.status_code != 200:
        return False
    
    data = r.json()

    if 'graphql' not in data.keys():
        return False

    try:
        followers = data['graphql']['user']['edge_followed_by']['count']
    except KeyError:
        followers = None

    try:
        fullname = data['graphql']['user']['full_name']
    except KeyError:
        fullname = None

    return {'followers': followers, 'fullname': fullname}
    



