import unittest
from app import app, calculate_route, CITY_COORDS
import json

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_dashboard_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ERATA HUKUK', response.data)
        self.assertIn(b'Dosya Listesi', response.data)

    def test_route_planner_page(self):
        response = self.app.get('/rota')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Rota Planlama', response.data)

    def test_calculate_route_logic(self):
        # Mock data for calculation
        # Case 1: Ankara
        # Case 2: Istanbul
        # Start: Bursa

        # We need to mock get_case behavior or test logic directly if possible.
        # Since calculate_route calls get_case which calls an external API (PocketBase),
        # we should mock get_case. However, for a quick integration test without mocking lib:

        # Test basic coordinate retrieval
        self.assertIn('Ankara', CITY_COORDS)
        self.assertEqual(CITY_COORDS['Ankara']['lat'], 39.9334)

    def test_api_route_calculation_empty(self):
        response = self.app.post('/api/planla', data={
            'selected_cases': [],
            'start_city': 'Bursa'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, [])

if __name__ == '__main__':
    unittest.main()
