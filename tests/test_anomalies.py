import unittest
from app.core.anomaly_engine import AnomalyEngine

class TestAnomalyEngine(unittest.TestCase):

    def setUp(self):
        self.engine = AnomalyEngine()

    def test_overbilling_detection(self):
        # 1 laptop at 65000 = 65000 + 18% tax (11700) = 76700 expected.
        # But vendor billed 90000 (13300 overbilled).
        invoice = {
            'invoice_number': 'INV-TEST-01',
            'vendor': 'Overcharge Corp',
            'billed_total': 90000.0,
            'tax_rate': 18.0,
            'discount_amount': 0.0,
            'items': [
                {'description': 'Generic Laptop', 'quantity': 1, 'unit_price': 65000.0, 'line_total': 65000.0}
            ]
        }
        res = self.engine.analyze_invoice(invoice)
        self.assertEqual(res['status'], 'SUSPICIOUS')
        anom_types = [a['anomaly_type'] for a in res['anomalies']]
        self.assertIn('OVERBILLING', anom_types)

        overbilling_anom = next(a for a in res['anomalies'] if a['anomaly_type'] == 'OVERBILLING')
        self.assertEqual(overbilling_anom['severity'], 'CRITICAL')
        self.assertAlmostEqual(overbilling_anom['difference'], 13300.0)

    def test_duplicate_item_detection(self):
        invoice = {
            'invoice_number': 'INV-TEST-02',
            'vendor': 'Stationery Direct',
            'billed_total': 2800.0,
            'tax_rate': 0.0,
            'items': [
                {'description': 'A4 Copier Paper', 'quantity': 1, 'unit_price': 1400.0, 'line_total': 1400.0},
                {'description': 'A4 Copier Paper', 'quantity': 1, 'unit_price': 1400.0, 'line_total': 1400.0}
            ]
        }
        res = self.engine.analyze_invoice(invoice)
        anom_types = [a['anomaly_type'] for a in res['anomalies']]
        self.assertIn('DUPLICATE_ITEM', anom_types)

    def test_duplicate_invoice_detection(self):
        context = {
            'duplicate_invoices': [
                {'invoice_id': 99, 'invoice_number': 'INV-EXISTING-1', 'vendor': 'Acme', 'invoice_date': '2026-01-01', 'billed_total': 5000.0}
            ]
        }
        invoice = {
            'invoice_number': 'INV-EXISTING-1',
            'vendor': 'Acme',
            'billed_total': 5000.0,
            'tax_rate': 0.0,
            'items': [
                {'description': 'Widget', 'quantity': 1, 'unit_price': 5000.0, 'line_total': 5000.0}
            ]
        }
        res = self.engine.analyze_invoice(invoice, context=context)
        anom_types = [a['anomaly_type'] for a in res['anomalies']]
        self.assertIn('DUPLICATE_INVOICE', anom_types)
        dup = next(a for a in res['anomalies'] if a['anomaly_type'] == 'DUPLICATE_INVOICE')
        self.assertEqual(dup['severity'], 'CRITICAL')

    def test_price_spike_against_reference_catalog(self):
        # Benchmark for Office Chair is 8500 (+15% tolerance max = 9775).
        # Billed at 14500 (+70.5% spike)
        def mock_ref_finder(desc, cat):
            if 'chair' in desc.lower():
                return {'expected_unit_price': 8500.0, 'tolerance_percent': 15.0}
            return None

        context = {'ref_finder': mock_ref_finder}
        invoice = {
            'invoice_number': 'INV-TEST-03',
            'vendor': 'Luxury Furniture',
            'billed_total': 14500.0,
            'tax_rate': 0.0,
            'items': [
                {'description': 'Ergonomic Office Chair', 'quantity': 1, 'unit_price': 14500.0, 'line_total': 14500.0}
            ]
        }
        res = self.engine.analyze_invoice(invoice, context=context)
        anom_types = [a['anomaly_type'] for a in res['anomalies']]
        self.assertIn('PRICE_ANOMALY', anom_types)
        price_anom = next(a for a in res['anomalies'] if a['anomaly_type'] == 'PRICE_ANOMALY')
        self.assertEqual(price_anom['severity'], 'CRITICAL')

if __name__ == '__main__':
    unittest.main()
