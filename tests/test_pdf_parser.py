import os
import unittest
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app.core.parsers import InvoiceParser, parse_invoice_pdf


class TestPdfParser(unittest.TestCase):

    def test_pdf_invoice_generation_and_parsing(self):
        pdf_path = os.path.join(os.path.dirname(__file__), 'temp_test_invoice.pdf')
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()

        story = [
            Paragraph("INVOICE", styles['Heading1']),
            Paragraph("Invoice Number: INV-PDF-2026", styles['Normal']),
            Paragraph("Vendor: Apex Hardware Supplies", styles['Normal']),
            Paragraph("Date: 2026-03-24", styles['Normal']),
            Spacer(1, 10),
            Paragraph("Dell Latitude 5420 Laptop 2 65000.00 130000.00", styles['Normal']),
            Spacer(1, 10),
            Paragraph("Tax (18%): 23400.00", styles['Normal']),
            Paragraph("Total: 153400.00", styles['Normal'])
        ]
        doc.build(story)

        try:
            with open(pdf_path, 'rb') as f:
                res = parse_invoice_pdf(f)
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        self.assertEqual(res['invoice_number'], "INV-PDF-2026")
        self.assertEqual(res['vendor'], "Apex Hardware Supplies")
        self.assertEqual(len(res['items']), 1)
        self.assertEqual(res['items'][0]['quantity'], 2.0)
        self.assertEqual(res['items'][0]['unit_price'], 65000.0)

    def test_ecommerce_flipkart_style_pdf_parsing(self):
        pdf_path = os.path.join(os.path.dirname(__file__), 'temp_flipkart_invoice.pdf')
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()

        story = [
            Paragraph("Tax Invoice", styles['Heading1']),
            Paragraph("Sold By: SuperComNet Pvt Ltd, Bengaluru", styles['Normal']),
            Paragraph("Invoice Number # FAB123456789", styles['Normal']),
            Paragraph("Invoice Date: 24-03-2026", styles['Normal']),
            Spacer(1, 10),
            # IGST format (1 tax column)
            Paragraph("Logitech Mouse M185 2 1200.00 -100.00 932.20 167.80 1100.00", styles['Normal']),
            # CGST/SGST format (2 tax columns)
            Paragraph("USB-C Hub 1 1000.00 0.00 847.46 76.27 76.27 1000.00", styles['Normal']),
            # Duplicate line (e.g. bundled Credit Note in same PDF) should be deduplicated
            Paragraph("USB-C Hub 1 1000.00 0.00 847.46 76.27 76.27 1000.00", styles['Normal']),
            Spacer(1, 10),
            Paragraph("Grand Total ₹ 2,100.00", styles['Normal'])
        ]
        doc.build(story)

        try:
            res = InvoiceParser.parse(pdf_path)
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        self.assertEqual(res['vendor'], "SuperComNet Pvt Ltd")
        self.assertEqual(res['invoice_number'], "FAB123456789")
        self.assertEqual(res['invoice_date'], "24-03-2026")
        self.assertEqual(res['billed_total'], 2100.0)
        self.assertEqual(len(res['items']), 2)
        self.assertEqual(res['items'][0]['description'], "Logitech Mouse M185")
        self.assertEqual(res['items'][0]['unit_price'], 550.0)
        self.assertEqual(res['items'][1]['description'], "USB-C Hub")


if __name__ == '__main__':
    unittest.main()
