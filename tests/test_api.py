import unittest
import os
import tempfile
import json
import io
from app import create_app
from app.config import Config

class TestApiConfig(Config):
    TESTING = True

class TestApiEndpoints(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        TestApiConfig.DATABASE_PATH = self.db_path
        self.app = create_app(TestApiConfig)
        self.client = self.app.test_client()

        # Login as Admin for testing
        self.client.post('/api/auth/login', json={
            'email': 'admin@iaod.local',
            'password': 'Admin@123'
        })

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_create_and_analyze_clean_invoice(self):
        payload = {
            'invoice_number': 'INV-2026-UNIT-01',
            'vendor': 'Dell India',
            'invoice_date': '2026-03-24',
            'tax_rate': 18.0,
            'tax_amount': 23400.0,
            'discount_amount': 0.0,
            'billed_total': 153400.0,
            'items': [
                {
                    'description': 'Dell Latitude 5420 Laptop',
                    'category': 'Electronics',
                    'quantity': 2,
                    'unit_price': 65000.0,
                    'line_total': 130000.0
                }
            ]
        }
        res = self.client.post('/api/invoices', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        inv_id = data['invoice_id']
        self.assertEqual(data['status'], 'NORMAL')
        self.assertEqual(data['total_anomalies'], 0)

        # Retrieve invoice details
        get_res = self.client.get(f'/api/invoices/{inv_id}')
        self.assertEqual(get_res.status_code, 200)
        inv_detail = get_res.get_json()
        self.assertEqual(inv_detail['invoice']['invoice_number'], 'INV-2026-UNIT-01')
        self.assertEqual(len(inv_detail['items']), 1)

    def test_overbilled_invoice_api(self):
        # 1 laptop at 65000 = 65000 + 18% tax (11700) = 76700 expected.
        # Billed: 95000 (discrepancy: +18300)
        payload = {
            'invoice_number': 'INV-2026-OVER-02',
            'vendor': 'Overcharge Corp',
            'invoice_date': '2026-03-24',
            'tax_rate': 18.0,
            'tax_amount': 11700.0,
            'discount_amount': 0.0,
            'billed_total': 95000.0,
            'items': [
                {
                    'description': 'Dell Latitude 5420 Laptop',
                    'category': 'Electronics',
                    'quantity': 1,
                    'unit_price': 65000.0,
                    'line_total': 65000.0
                }
            ]
        }
        res = self.client.post('/api/invoices', json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['status'], 'SUSPICIOUS')
        self.assertGreater(data['total_anomalies'], 0)

        # Retrieve anomalies endpoint
        anom_res = self.client.get(f"/api/invoices/{data['invoice_id']}/anomalies")
        self.assertEqual(anom_res.status_code, 200)
        anoms = anom_res.get_json()['anomalies']
        types = [a['anomaly_type'] for a in anoms]
        self.assertIn('OVERBILLING', types)

    def test_file_upload_csv(self):
        csv_content = """invoice_number,vendor,invoice_date,description,category,quantity,unit_price,line_total,billed_total
INV-UPLOAD-101,Office Mart,2026-03-24,Ergonomic Office Chair,Furniture,2,8500.0,17000.0,17000.0
"""
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_upload.csv')
        }
        res = self.client.post('/api/invoices', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        resp_data = res.get_json()
        self.assertIn('invoice_id', resp_data)

    def test_download_report_pdf_and_json(self):
        # Create an invoice first
        payload = {
            'invoice_number': 'INV-REPORT-TEST',
            'vendor': 'Report Test Corp',
            'invoice_date': '2026-03-24',
            'tax_rate': 0.0,
            'billed_total': 8500.0,
            'items': [
                {'description': 'Ergonomic Office Chair', 'quantity': 1, 'unit_price': 8500.0, 'line_total': 8500.0}
            ]
        }
        create_res = self.client.post('/api/invoices', json=payload)
        inv_id = create_res.get_json()['invoice_id']

        # Download PDF
        pdf_res = self.client.get(f'/api/reports/{inv_id}/download?format=pdf')
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, 'application/pdf')

        # Download JSON
        json_res = self.client.get(f'/api/reports/{inv_id}/download?format=json')
        self.assertEqual(json_res.status_code, 200)
        self.assertEqual(json_res.mimetype, 'application/json')

    def test_dashboard_summary_api(self):
        res = self.client.get('/api/dashboard/summary')
        self.assertEqual(res.status_code, 200)
        stats = res.get_json()
        self.assertIn('total_invoices', stats)
        self.assertIn('normal_invoices', stats)
        self.assertIn('suspicious_invoices', stats)
        self.assertIn('total_overbilled', stats)

    def test_reference_prices_api(self):
        # List reference prices
        list_res = self.client.get('/api/reference-prices')
        self.assertEqual(list_res.status_code, 200)
        initial_count = list_res.get_json()['count']

        # Add new reference price
        add_res = self.client.post('/api/reference-prices', json={
            'item_name': 'Test Projector 4K',
            'category': 'Electronics',
            'expected_unit_price': 80000.0,
            'tolerance_percent': 10.0
        })
        self.assertEqual(add_res.status_code, 201)
        ref_id = add_res.get_json()['reference_id']

        # Delete added reference price
        del_res = self.client.delete(f'/api/reference-prices/{ref_id}')
        self.assertEqual(del_res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
