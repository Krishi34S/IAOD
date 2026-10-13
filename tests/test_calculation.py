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

    def test_line_item_math_error(self):
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

if __name__ == '__main__':
    unittest.main()
