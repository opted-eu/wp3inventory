# Ugly hack to allow absolute import from the root folder
# whatever its name is. Please forgive the heresy.

if __name__ == "__main__":
    from sys import path
    from os.path import dirname
    from flask import request, url_for
    import unittest

    path.append(dirname(path[0]))
    from test_setup import BasicTestSetup
    from flaskinventory import dgraph


class TestRoutesLoggedOut(BasicTestSetup):

    """ View Routes """

    def test_view_search(self):
        if self.verbatim:
            print('-- test_view_search() --\n')

        # /search?query=bla
        with self.client as c:

            response = c.get('/search',
                             follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(request.path, url_for('main.home'))

            response = c.get('/search', query_string={'query': 'bla'},
                             follow_redirects=True)

            self.assertEqual(response.status_code, 200)

            response = c.get('/search', query_string={'query': self.derstandard_facebook},
                             follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(request.path, url_for('view.view_generic',
                                                   unique_name='derstandard_facebook',
                                                   dgraph_type='Source'))

    def test_view_uid(self):
        if self.verbatim:
            print('-- test_view_uid() --\n')

        # /view
        # /view?uid=<uid>
        # /view/uid/<uid>
        with self.client as c:

            response = c.get('/view',
                             follow_redirects=True)

            self.assertEqual(response.status_code, 404)

            response = c.get('/view',
                             query_string={'uid': self.derstandard_instagram},
                             follow_redirects=True)
            self.assertEqual(request.path, url_for('view.view_generic',
                                                   unique_name='derstandard_instagram',
                                                   dgraph_type='Source'))
            self.assertEqual(response.status_code, 200)

            response = c.get('/view/uid/' + self.derstandard_mbh_uid,
                             follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(request.path, url_for('view.view_generic',
                                                   unique_name='derstandard_mbh',
                                                   dgraph_type='Organization'))

            for channel in self.channels:
                response = c.get('/view/uid/' + channel,
                                 follow_redirects=True)
                self.assertEqual(response.status_code, 200)

                response = c.get('/view',
                                 query_string={'uid': channel},
                                 follow_redirects=True)
                self.assertEqual(response.status_code, 200)

            # edge cases
            response = c.get('/view/uid/0x0', follow_redirects=True)
            self.assertEqual(response.status_code, 404)

            response = c.get('/view/uid/0', follow_redirects=True)
            self.assertEqual(response.status_code, 404)

    def test_view_uid_pending(self):
        if self.verbatim:
            print('-- test_view_uid_pending() --\n')

        # pending entries

        # /view?uid=<uid>
        with self.client as c:
            # view some one elses entry
            mutation = dgraph.mutation(
                {'uid': self.derstandard_print, 'entry_review_status': 'pending'})

            response = c.get('/view',
                             query_string={'uid': self.derstandard_print},
                             follow_redirects=True)

            if not self.logged_in:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for('users.login'))
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 403)
            elif self.logged_in == 'reviewer':
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for(
                    'view.view_generic', unique_name="derstandard_print", dgraph_type='Source'))

            # view one's own entry
            mutation = dgraph.mutation(
                {'uid': self.derstandard_print,
                 'entry_review_status': 'pending',
                 'entry_added': {'uid': self.contributor_uid}})

            response = c.get('/view',
                             query_string={'uid': self.derstandard_print},
                             follow_redirects=True)

            if not self.logged_in:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for('users.login'))
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 200)
            elif self.logged_in == 'reviewer':
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for(
                    'view.view_generic', unique_name="derstandard_print", dgraph_type='Source'))

            mutation = dgraph.mutation(
                {'uid': self.derstandard_print,
                 'entry_review_status': 'accepted',
                 'entry_added': {'uid': self.admin_uid}})

    def test_view_uid_draft(self):
        if self.verbatim:
            print('-- test_view_uid_draft() --\n')

        # draft entries

        # /view?uid=<uid>
        with self.client as c:

            mutation = dgraph.mutation(
                {'uid': self.derstandard_print,
                 'entry_review_status': 'draft'})

            response = c.get('/view',
                             query_string={'uid': self.derstandard_print},
                             follow_redirects=True)

            if not self.logged_in:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for('users.login'))
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 403)
            elif self.logged_in == 'reviewer':
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for(
                    'view.view_generic', unique_name="derstandard_print", dgraph_type='Source'))

            # view one's own entry
            mutation = dgraph.mutation(
                {'uid': self.derstandard_print,
                 'entry_review_status': 'draft',
                 'entry_added': {'uid': self.contributor_uid}})

            response = c.get('/view',
                             query_string={'uid': self.derstandard_print},
                             follow_redirects=True)

            if not self.logged_in:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for('users.login'))
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 200)
            elif self.logged_in == 'reviewer':
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for(
                    'view.view_generic', unique_name="derstandard_print", dgraph_type='Source'))

            mutation = dgraph.mutation(
                {'uid': self.derstandard_print,
                 'entry_review_status': 'accepted',
                 'entry_added': {'uid': self.admin_uid}})

    def test_view_rejected(self):
        if self.verbatim:
            print('-- test_view_rejected() --\n')

        # /view
        # /view?uid=<uid>
        # /view/uid/<uid>
        with self.client as c:

            response = c.get('/view/rejected/')
            self.assertEqual(response.status_code, 404)

            response = c.get('/view/rejected/' + self.rejected_entry)

            if not self.logged_in:
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

    def test_view_generic(self):
        if self.verbatim:
            print('-- test_view_generic() --\n')

        # /view/<string:dgraph_type>/uid/<uid>
        # /view/<string:dgraph_type>/<string:unique_name>

        with self.client as c:

            for organization in self.organizations:
                response = c.get('/view/Organzation/uid/' + organization,
                                 follow_redirects=True)
                self.assertEqual(response.status_code, 200)

            for source in self.sources:
                response = c.get('/view/Source/uid/' + source,
                                 follow_redirects=True)
                self.assertEqual(response.status_code, 200)

            for channel in self.channels:
                response = c.get('/view/channel/uid/' + channel,
                                 follow_redirects=True)
                self.assertEqual(response.status_code, 200)

            for country in self.countries:
                response = c.get('/view/country/uid/' + country,
                                 follow_redirects=True)
                self.assertEqual(response.status_code, 200)

            response = c.get('/view/MetaVar/uid/' + self.derstandard_facebook)
            self.assertEqual(response.status_code, 302)

            response = c.get('/view/Tool/uid/0xffffffffffffff',
                             follow_redirects=True)
            self.assertEqual(response.status_code, 404)

    """ Review Routes """

    def test_overview(self):
        if self.verbatim:
            print('-- test_overview() --\n')

        # /review/overview
        # /review/overview?country=0x123&entity=0x234
        with self.client as c:

            response = c.get('/review/overview')
            if not self.logged_in:
                # redirect to login page
                self.assertEqual(response.status_code, 302)
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            response = c.get('/review/overview',
                             query_string={'country': self.austria_uid})
            if not self.logged_in:
                # redirect to login page
                self.assertEqual(response.status_code, 302)
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            response = c.get('/review/overview',
                             query_string={'entity': 'Tool'})
            if not self.logged_in:
                # redirect to login page
                self.assertEqual(response.status_code, 302)
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

    def test_review_submit(self):
        if self.verbatim:
            print('-- test_review_submit() --\n')

        # POST /review/submit

        # prepare a temp entry
        tmp_entry = {'uid': '_:tempentry',
                     'dgraph.type': ['Entry', 'Source'],
                     'name': 'Temp Entry',
                     'unique_name': 'tmp_entry',
                     'creation_date': '2022-05-17T10:00:00',
                     'entry_added': {'uid': self.contributor_uid,
                                     'entry_added|timestamp': '2022-05-17T10:00:00',
                                     'entry_added|ip': '192.168.0.1'
                                     }
                     }

        # accept entry

        with self.client as c:
            response = dgraph.mutation(tmp_entry)
            tmp_entry_uid = response.uids['tempentry']

        delete_tmp = {'uid': tmp_entry_uid,
                      'dgraph.type': None,
                      'name': None,
                      'unique_name': None,
                      'entry_added': {'uid': self.contributor_uid},
                      'creation_date': None}

        with self.client as c:

            response = c.post('/review/submit',
                              data={'uid': tmp_entry_uid, 'accept': True},
                              follow_redirects=True)
            if not self.logged_in:
                # redirect to login page
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for('users.login'))
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            dgraph.delete(delete_tmp)

        # reject entry

        with self.client as c:
            response = dgraph.mutation(tmp_entry)
            tmp_entry_uid = response.uids['tempentry']

        delete_tmp['uid'] = tmp_entry_uid

        with self.client as c:

            response = c.post('/review/submit',
                              data={'uid': tmp_entry_uid, 'reject': True},
                              follow_redirects=True)
            if not self.logged_in:
                # redirect to login page
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.path, url_for('users.login'))
            elif self.logged_in == 'contributor':
                self.assertEqual(response.status_code, 403)
            else:
                self.assertEqual(response.status_code, 200)

            dgraph.delete(delete_tmp)


class TestRoutesLoggedInContributor(TestRoutesLoggedOut):

    user_login = {'email': 'contributor@opted.eu',
                  'password': 'contributor123'}
    logged_in = 'contributor'

    def setUp(self):
        with self.client:
            response = self.client.post(
                '/login', data=self.user_login)
            assert response.status_code == 302
            assert "profile" in response.location

    def tearDown(self):
        with self.client:
            self.client.get('/logout')


class TestRoutesLoggedInReviewer(TestRoutesLoggedInContributor):

    user_login = {'email': 'reviewer@opted.eu', 'password': 'reviewer123'}
    logged_in = 'reviewer'


class TestRoutesLoggedInAdmin(TestRoutesLoggedInContributor):

    user_login = {'email': 'wp3@opted.eu', 'password': 'admin123'}
    logged_in = 'admin'


if __name__ == "__main__":
    unittest.main()
