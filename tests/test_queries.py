#  Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.

if __name__ == "__main__":
    import unittest
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))
    from test_setup import BasicTestSetup
    from flaskinventory.view.routes import build_query_string
    from flaskinventory import dgraph

class TestQueries(BasicTestSetup):

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

        with self.client as c:
            query = {"languages": ["de"],
                     "publication_kind": "alternative media",
                     "channel": self.channel_print,
                     'json': True}

            response = c.get('/query',
                             query_string=query)

            self.assertEqual(
                response.json['result'][0]['unique_name'], "direkt_print")

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
        pass
        # No queryable integer predicate in current data model
        # with self.client as c:
        #     query = {"publication_cycle_weekday": 3}

        #     response = c.get('/query', query_string=query)
        #     self.assertEqual(response.json['result'][0]['unique_name'], 'falter_print')

    def test_facet_filters(self):
        with self.client as c:
            query = {"audience_size|unit": "copies sold",
                     "audience_size|count": 52000,
                     "audience_size|count*operator": 'gt',
                     "json": True}

            response = c.get('/query',
                             query_string=query)
            self.assertEqual(
                response.json['result'][0]['unique_name'], 'derstandard_print')

    def test_type_filters(self):

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
    unittest.main(verbosity=2)
