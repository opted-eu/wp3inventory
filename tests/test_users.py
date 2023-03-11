
if __name__ == "__main__":
    from sys import path
    from os.path import dirname
    import unittest

    path.append(dirname(path[0]))

    from flask_login import current_user
    from flaskinventory import create_app, AnonymousUser, dgraph
    from flaskinventory.users.dgraph import User, create_user
    from test_setup import BasicTestSetup


class TestUsers(BasicTestSetup):

    """
        Test cases for handling simple user actions
    """

    def test_login(self):
        # print('-- test_login() --\n')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'contributor@opted.eu', 'password': 'contributor123'})
            self.assertIsInstance(current_user, User)
            self.assertEqual(current_user.user_displayname, 'Contributor')
            self.client.get('/logout')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'reviewer@opted.eu', 'password': 'reviewer123'})
            self.assertIsInstance(current_user, User)
            self.assertEqual(current_user.user_displayname, 'Reviewer')
            self.client.get('/logout')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'wp3@opted.eu', 'password': 'admin123'})
            self.assertIsInstance(current_user, User)
            self.assertEqual(current_user.user_displayname, 'Admin')
            self.client.get('/logout')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'notinsystem@opted.eu', 'password': 'admin123'})
            self.assertIsInstance(current_user, AnonymousUser)

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'wp3@opted.eu', 'password': 'wrongpassword'})
            self.assertIsInstance(current_user, AnonymousUser)

    def test_create_user(self):
        weird_pw = '!"§$%&/()=?ß`´\}[]{[}*+~#<>|_.-.,;:µ1/o6t8K%70I*"h>c7`].Aw.Hx'
        with self.app.app_context():
            weird_user = {'email': "weird@user.com",
                          'pw': weird_pw}
            new_uid = create_user(weird_user)
            dgraph.update_entry({'account_status': "active"}, uid=new_uid)

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'weird@user.com', 'password': weird_pw})
            self.assertIsInstance(current_user, User)
            self.client.get('/logout')

        with self.client:
            response = self.client.post(
                '/login', data={'email': 'weird@user.com', 'password': weird_pw})
            self.assertIsInstance(current_user, User)
            self.client.get('/users/delete')


if __name__ == "__main__":
    unittest.main(verbosity=2)
