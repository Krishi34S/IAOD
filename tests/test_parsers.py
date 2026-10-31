import unittest
import io
from app.core.parsers import parse_invoice_json, parse_invoice_csv, parse_uploaded_invoice
from app.core.validator import InvoiceValidationError

class TestParsers(unittest.TestCase):

    def test_json_parser_valid(self):
        json_data = '''{
            "invoice_number": "INV-JSON-001",
            "vendor": "Dell India",
            "invoice_date": "2026-03-10",
            "billed_total": 65000.0,
            "items": [
                {"description": "Dell Latitude Laptop", "quantity": 1, "unit_price": 65000.0, "line_total": 65000.0}
            ]
        }'''
        res = parse_invoice_json(json_data)
        self.assertEqual(res['invoice_number'], "INV-JSON-001")
        self.assertEqual(res['vendor'], "Dell India")
        self.assertEqual(len(res['items']), 1)

    def test_flat_csv_parser(self):
        csv_data = """invoice_number,vendor,invoice_date,description,category,quantity,unit_price,line_total,billed_total
INV-CSV-99,Acme Supplies,2026-02-15,A4 Paper,Stationery,5,1400.0,7000.0,7000.0
"""
        res = parse_invoice_csv(csv_data)
        self.assertEqual(res['invoice_number'], "INV-CSV-99")
        self.assertEqual(res['vendor'], "Acme Supplies")
        self.assertEqual(len(res['items']), 1)
        self.assertEqual(res['items'][0]['quantity'], 5.0)

    def test_header_style_csv_parser(self):
        csv_data = """Invoice Number,INV-HDR-100
Vendor,Global Networks
Date,2026-02-20
Billed Total,28000.0
[Items]
Description,Category,Quantity,Unit Price,Line Total
Gigabit Switch,Networking,1,28000.0,28000.0
"""
        res = parse_invoice_csv(csv_data)
        self.assertEqual(res['invoice_number'], "INV-HDR-100")
        self.assertEqual(res['vendor'], "Global Networks")
        self.assertEqual(len(res['items']), 1)

    def test_missing_fields_validation_error(self):
        # Missing vendor and line items
        invalid_json = '{"invoice_number": "INV-X"}'
        with self.assertRaises(InvoiceValidationError):
            parse_invoice_json(invalid_json)

if __name__ == '__main__':
    unittest.main()
