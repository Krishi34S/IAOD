import unittest
from app.core.calculation_engine import verify_invoice_calculations

class TestCalculationEngine(unittest.TestCase):

    def test_clean_calculation(self):
        invoice = {
            'billed_total': 153400.0,
            'tax_rate': 18.0,
            'discount_amount': 0.0,
            'items': [
                {'description': 'Laptop', 'quantity': 2, 'unit_price': 65000.0, 'line_total': 130000.0}
            ]
        }
        res = verify_invoice_calculations(invoice)
        self.assertEqual(res['expected_subtotal'], 130000.0)
        self.assertEqual(res['expected_tax'], 23400.0)
        self.assertEqual(res['expected_total'], 153400.0)
        self.assertEqual(res['total_discrepancy'], 0.0)
        self.assertEqual(len(res['calculation_errors']), 0)

    def test_line_item_math_error(self):
        # Quantity 3 * 8500 = 25500, but billed as 28000
        invoice = {
            'billed_total': 33040.0,
            'tax_rate': 18.0,
            'discount_amount': 0.0,
            'items': [
                {'description': 'Chair', 'quantity': 3, 'unit_price': 8500.0, 'line_total': 28000.0}
            ]
        }
        res = verify_invoice_calculations(invoice)
        self.assertEqual(len(res['calculation_errors']), 1)
        err = res['calculation_errors'][0]
        self.assertEqual(err['expected_line_total'], 25500.0)
        self.assertEqual(err['billed_line_total'], 28000.0)
        self.assertEqual(err['difference'], 2500.0)

    def test_tax_and_discount_calculation(self):
        # 1000 subtotal, 100 discount = 900 taxable base * 10% tax = 90 tax => 990 total
        invoice = {
            'billed_total': 990.0,
            'tax_rate': 10.0,
            'tax_amount': 90.0,
            'discount_amount': 100.0,
            'items': [
                {'description': 'Item A', 'quantity': 10, 'unit_price': 100.0, 'line_total': 1000.0}
            ]
        }
        res = verify_invoice_calculations(invoice)
        self.assertEqual(res['expected_subtotal'], 1000.0)
        self.assertEqual(res['expected_tax'], 90.0)
        self.assertEqual(res['expected_total'], 990.0)
        self.assertEqual(res['total_discrepancy'], 0.0)

    def test_invalid_negative_discount(self):
        invoice = {
            'billed_total': 1000.0,
            'tax_rate': 0.0,
            'discount_amount': -50.0,
            'items': [
                {'description': 'Item B', 'quantity': 1, 'unit_price': 1000.0, 'line_total': 1000.0}
            ]
        }
        res = verify_invoice_calculations(invoice)
        self.assertIsNotNone(res['discount_error'])

if __name__ == '__main__':
    unittest.main()
