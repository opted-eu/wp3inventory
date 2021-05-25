import time
import requests
import geocoder
import feedparser
from urllib.robotparser import RobotFileParser
import urllib.parse
from bs4 import BeautifulSoup as bs4
import validators




def get_geocoords(address):
    time.sleep(5)
    r = geocoder.osm(address)
    if r.status_code != 200:
        return False
    return r.geojson.get('features')[0].get('geometry')


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
        if r.headers['Content-Type'] in ['application/xml']:
            return [site + '/rss']
    except Exception:
        pass

    r = requests.get(site)
    result = []
    possible_feeds = []
    html = bs4(r.content, 'lxml')
    feed_urls = html.findAll("link", rel="alternate")
    if len(feed_urls) > 1:
        for f in feed_urls:
            t = f.get("type",None)
            if t:
                if "rss" in t or "xml" in t:
                    href = f.get("href",None)
                    if href:
                        possible_feeds.append(href)
    parsed_url = urllib.parse.urlparse(site)
    base = parsed_url.scheme+"://"+parsed_url.hostname
    atags = html.findAll("a")
    for a in atags:
        href = a.get("href",None)
        if href:
            if "xml" in href or "rss" in href or "feed" in href:
                possible_feeds.append(base+href)
    for url in list(set(possible_feeds)):
        parsed_feed_url = urllib.parse.urlparse(url)
        feed_url = "http://" + parsed_feed_url.netloc + parsed_feed_url.path
        f = feedparser.parse(feed_url)
        if len(f.entries) > 0:
            if url not in result:
                result.append(feed_url)
    return result
