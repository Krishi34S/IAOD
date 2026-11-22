import unittest
import os
import tempfile
from app import create_app
from app.config import Config

class TestAuthConfig(Config):
    TESTING = True

class TestAuth(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        TestAuthConfig.DATABASE_PATH = self.db_path
        self.app = create_app(TestAuthConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_user_registration_and_login(self):
        # 1. Register a new user
        reg_res = self.client.post('/api/auth/register', json={
            'name': 'Test User',
            'email': 'newuser@iaod.local',
            'password': 'Password@123',
            'role': 'user'
        })
        self.assertEqual(reg_res.status_code, 201)
        data = reg_res.get_json()
        self.assertEqual(data['user']['email'], 'newuser@iaod.local')

        # 2. Login with correct credentials
        login_res = self.client.post('/api/auth/login', json={
            'email': 'newuser@iaod.local',
            'password': 'Password@123'
        })
        self.assertEqual(login_res.status_code, 200)

        # 3. Check /api/auth/me
        me_res = self.client.get('/api/auth/me')
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()['name'], 'Test User')

        # 4. Logout
        logout_res = self.client.post('/api/auth/logout')
        self.assertEqual(logout_res.status_code, 200)

        # 5. Access protected route after logout -> 401
        me_res_after = self.client.get('/api/auth/me')
        self.assertEqual(me_res_after.status_code, 401)

    def test_invalid_login(self):
        res = self.client.post('/api/auth/login', json={
            'email': 'admin@iaod.local',
            'password': 'WrongPassword'
        })
        self.assertEqual(res.status_code, 401)

    def test_default_seeded_accounts(self):
        # Admin account
        res = self.client.post('/api/auth/login', json={
            'email': 'admin@iaod.local',
            'password': 'Admin@123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['user']['role'], 'admin')

if __name__ == '__main__':
    unittest.main()
