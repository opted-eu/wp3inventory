# output from original sanitizer
import datetime
# sanitizer.newsource

{
    'dgraph.type': ['Source', 'Entry'],
    'country': ["0x295e"],
    'other_names': ['https://www.tagesschau.de/', 'Aktuelle Nachrichten - Inland Ausland Wirtschaft Kultur Sport - ARD Tagesschau', 'Tagesschau', 'Tagesthemen'],
    'channel': "0x2954",
    'name': 'www.tagesschau.de',
    'channel_url': 'https://www.tagesschau.de/',
    'website_allows_comments': 'no',
    'founded': '2000',
    'payment_model': 'free',
    'contains_ads': 'no',
    'publication_kind': ['tv show'],
    'special_interest': True,
    'topical_focus': ['politics'],
    'publication_cycle': 'multiple times per week',
    'publication_cycle_weekday': [1, 2, 3, 4, 5, 6, 7],
    'geographic_scope': 'national',
    'languages': ['de'],
    'entry_notes': 'Some notes',
    'party_affiliated': 'no',
    'related': ["_:https_twitter_com_tagesschau_twitter", "_:https_www_facebook_com_tagesschau_facebook"],
    'channel_feeds': ["https://www.tagesschau.de/xml/rss2/"],
    'unique_name': 'https_www_tagesschau_de_website',
    'entry_added': "0x2947",
    'entry_review_status': 'pending',
    'creation_date': datetime.datetime(2022, 3, 2, 17, 8, 38, 669202, tzinfo=datetime.timezone.utc)
}

# sanitizer.orgs
[
    {
        'uid': 'bla', # uid gets popped away!
        'publishes': "_:newsource",
        'is_person': False,
        'dgraph.type': ['Organization', 'Entry'],
        'entry_added': "0x2947",
        'entry_review_status': 'pending',
        'creation_date': datetime.datetime(2022, 3, 2, 17, 8, 5, 545894, tzinfo=datetime.timezone.utc),
        'name': 'ARD',
        'address_geo': {'type': 'Point',
                        'coordinates': [124.5969940383382, -8.13270305]},
        'address_string': 'Bandar Udara Mali, Alor, Nusa Tenggara Timur, Indonesia',
        'wikidataID': 49653,
        'other_names': [],
        'founded': datetime.datetime(1950, 6, 5, 0, 0, tzinfo=tzutc()),
        'country': "0x295e",
        'address': 'Stuttgart',
        'unique_name': 'ard'
    },
    {
        'publishes': "_:newsource", 'is_person': False
    },
    {
        'publishes': "_:newsource", 'is_person': True,
        'dgraph.type': ['Organization', 'Entry'],
        'entry_added': "0x2947",
        'entry_review_status': 'pending',
        'creation_date': datetime.datetime(2022, 3, 2, 17, 8, 7, 496108, tzinfo=datetime.timezone.utc),
        'name': 'Caren Mioska',
        'unique_name': 'caren_mioska'
    }
]

# sanitizer.related
[
    {'related': ["_:newsource", "_:https_www_facebook_com_tagesschau_facebook"],
        'dgraph.type': ['Source', 'Entry'],
        'entry_added': "0x2947",
        'entry_review_status': 'draft',
        'creation_date': datetime.datetime(2022, 3, 2, 17, 8, 37, 965382, tzinfo=datetime.timezone.utc),
        'name': 'https://twitter.com/tagesschau',
        'unique_name': 's1BzcMnyHPY',
        'channel': "0x2955",
        'publication_kind': ['tv show'],
        'special_interest': True,
        'topical_focus': ['politics'],
        'geographic_scope': 'national',
        'country': ["0x295e"],
        'languages': ['de'],
        'party_affiliated': 'no'},
    {
        'related': ["_:newsource", "_:https_twitter_com_tagesschau_twitter"],
        'dgraph.type': ['Source', 'Entry'],
        'entry_added': "0x2947",
        'entry_review_status': 'draft',
        'creation_date': datetime.datetime(2022, 3, 2, 17, 8, 37, 965463, tzinfo=datetime.timezone.utc),
        'name': 'https://www.facebook.com/tagesschau',
        'unique_name': 'dK1cpxYMnq0',
        'channel': "0x294f",
        'publication_kind': ['tv show'],
        'special_interest': True,
        'topical_focus': ['politics'],
        'geographic_scope': 'national',
        'country': ["0x295e"],
        'languages': ['de'],
        'party_affiliated': 'no'
    }
]
