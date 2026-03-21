import unittest
from flask import json
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.db.user import get_or_create


class ExportAPIIntegrationTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        # Ensure we have a user with a token
        self.user = get_or_create(self.db_conn, 1, 'testuser')
        self.auth_headers = {'Authorization': f'Token {self.user["auth_token"]}'}

    def test_create_get_list_export(self):
        """ Test the complete flow of creating, checking, and listing exports """
        
        # 1. Create an export task
        response = self.client.post('/1/export/', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIn('export_id', data)
        self.assertEqual(data['status'], 'waiting')
        self.assertEqual(data['type'], 'export_all_user_data')
        
        export_id = data['export_id']
        
        # 2. Check the status of the export
        response = self.client.get(f'/1/export/{export_id}', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['export_id'], export_id)
        # In a test environment without a real background worker, status remains 'waiting'
        self.assertEqual(data['status'], 'waiting')

        # 3. List all exports
        response = self.client.get('/1/export/', headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        
        # Verify our export is in the list
        found = False
        for export in data:
            if export['export_id'] == export_id:
                found = True
                break
        self.assertTrue(found, "Created export not found in list")

    def test_export_unauthorized(self):
        """ Test that endpoints require authentication """
        response = self.client.post('/1/export/')
        self.assertEqual(response.status_code, 401)
        
        response = self.client.get('/1/export/')
        self.assertEqual(response.status_code, 401)

    def test_get_nonexistent_export(self):
        """ Test getting a non-existent export """
        # Assuming 999999 is an ID that doesn't exist
        response = self.client.get('/1/export/999999', headers=self.auth_headers)
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
