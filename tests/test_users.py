
if __name__ == "__main__":
    from sys import path
    from os.path import dirname

    path.append(dirname(path[0]))

import unittest
from flask_login import current_user
from flaskinventory import create_app, AnonymousUser
from flaskinventory.users.dgraph import User


class TestUsers(unittest.TestCase):

    """
        Test cases for handling simple user actions
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(config_json="test_config.json")
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        return super().tearDownClass()

    def setUp(self):
        pass

    def tearDown(self):
        pass

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


if __name__ == "__main__":
    unittest.main()
