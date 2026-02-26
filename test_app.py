import unittest
import os
import io
import pandas as pd

# Set ENV before importing app to avoid default postgres connection attempt
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import app, db, Case
import json

class TestApp(unittest.TestCase):

    def setUp(self):
        # Ensure we are in testing mode
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        self.app_context = app.app_context()
        self.app_context.push()

        # Depending on how Flask-SQLAlchemy was init, it might have created an engine already.
        # But sqlite memory is fresh per connection usually.
        db.create_all()

        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_dashboard_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'ERATA HUKUK', response.data)

    def test_create_and_get_case(self):
        new_case = Case(
            case_no='2024/1',
            client='Test Client',
            city='Ankara',
            status='Aktif'
        )
        db.session.add(new_case)
        db.session.commit()

        response = self.client.get('/')
        self.assertIn(b'2024/1', response.data)
        self.assertIn(b'Test Client', response.data)

    def test_route_calculation_api(self):
        c1 = Case(case_no='C1', client='Client 1', city='Ankara', lat=39.9, lon=32.8)
        c2 = Case(case_no='C2', client='Client 2', city='Istanbul', lat=41.0, lon=28.9)
        db.session.add_all([c1, c2])
        db.session.commit()

        c1_id = c1.id
        c2_id = c2.id

        response = self.client.post('/api/planla', data={
            'selected_cases': [c1_id, c2_id],
            'start_city': 'Bursa'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_download_template(self):
        response = self.client.get('/api/download_template')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_upload_excel(self):
        # Create a sample Excel file in memory
        df = pd.DataFrame({
            'case_no': ['2024/TEST'],
            'client': ['Test Client'],
            'city': ['Ankara'],
            'status': ['Aktif']
        })
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        response = self.client.post('/api/upload_excel', data={
            'file': (output, 'test.xlsx')
        }, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 302) # Redirects to index

        # Verify data inserted
        case = Case.query.filter_by(case_no='2024/TEST').first()
        self.assertIsNotNone(case)
        self.assertEqual(case.client, 'Test Client')
        self.assertEqual(case.city, 'Ankara')

        # Test Duplicate Prevention
        # Create a new BytesIO since the previous one might be closed
        output2 = io.BytesIO()
        with pd.ExcelWriter(output2, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output2.seek(0)

        response = self.client.post('/api/upload_excel', data={
            'file': (output2, 'test.xlsx')
        }, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 302)

        # Count should still be 1
        count = Case.query.filter_by(case_no='2024/TEST').count()
        self.assertEqual(count, 1)

if __name__ == '__main__':
    unittest.main()
