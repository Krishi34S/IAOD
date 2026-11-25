import os
import re
import pdfplumber
import csv
import json

class InvoiceParser:
    @staticmethod
    def parse(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return InvoiceParser.parse_pdf(file_path)
        elif ext == '.csv':
            return InvoiceParser.parse_csv(file_path)
        elif ext == '.json':
            return InvoiceParser.parse_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def parse_pdf(file_path):
        data = {
            "vendor": "Unknown",
            "invoice_number": "Unknown",
            "invoice_date": "Unknown",
            "billed_total": 0.0,
            "items": []
        }
        vendor_pattern = re.compile(r"Sold By:\s*(.+?)(?:,|$)", re.IGNORECASE)
        invoice_num_pattern = re.compile(r"(?:Invoice Number\s*#|Original Invoice Number:)\s*([A-Z0-9\-]+)", re.IGNORECASE)
        date_pattern = re.compile(r"Invoice Date:\s*([\d\-]+)", re.IGNORECASE)
        grand_total_pattern = re.compile(r"Grand Total[\s\r\n]*(?:₹|Rs\.?)?\s*([\d,]+\.\d{2})", re.IGNORECASE)

        ecommerce_item_pattern = re.compile(
            r"^(?P<title>.*?)\s+"
            r"(?P<qty>\d+)\s+"
            r"(?P<gross>\d+\.\d{2})\s+"
            r"(?P<discount>-?\d+\.\d{2})\s+"
            r"(?P<taxable>\d+\.\d{2})\s+"
            r"(?P<tax1>\d+\.\d{2})\s+"
            r"(?:(?P<tax2>\d+\.\d{2})\s+)?"
            r"(?P<total>\d+\.\d{2})$"
        )
        generic_item_pattern = re.compile(
            r"^(?P<title>.+?)\s+"
            r"(?P<qty>\d+(?:\.\d+)?)\s+"
            r"(?P<price>\d+(?:\.\d{2})?)\s+"
            r"(?P<total>\d+(?:\.\d{2})?)$"
        )

        with pdfplumber.open(file_path) as pdf:
            found_grand_total = False
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                if data["vendor"] == "Unknown":
                    v_match = vendor_pattern.search(text)
                    if v_match: data["vendor"] = v_match.group(1).strip()
                if data["invoice_number"] == "Unknown":
                    inv_match = invoice_num_pattern.search(text)
                    if inv_match: data["invoice_number"] = inv_match.group(1).strip()
                if data["invoice_date"] == "Unknown":
                    d_match = date_pattern.search(text)
                    if d_match: data["invoice_date"] = d_match.group(1).strip()
                if not found_grand_total:
                    gt_match = grand_total_pattern.search(text)
                    if gt_match:
                        data["billed_total"] = float(gt_match.group(1).replace(',', ''))
                        found_grand_total = True

                for line in text.split('\n'):
                    line = line.strip()
                    if line.startswith("Total") or line.startswith("Shipping") or line.startswith("Grand Total"):
                        continue
                    ecom_match = ecommerce_item_pattern.match(line)
                    if ecom_match:
                        title = ecom_match.group("title").strip()
                        qty = float(ecom_match.group("qty"))
                        total = float(ecom_match.group("total"))
                        if not any(i["description"] == title and i["line_total"] == total for i in data["items"]):
                            data["items"].append({
                                "description": title, "category": "General", "quantity": qty,
                                "unit_price": total / qty if qty > 0 else 0, "line_total": total
                            })
                        continue
                    gen_match = generic_item_pattern.match(line)
                    if gen_match:
                        if "page" in line.lower() or "date" in line.lower():
                            continue
                        title = gen_match.group("title").strip()
                        total = float(gen_match.group("total"))
                        if not any(i["description"] == title and i["line_total"] == total for i in data["items"]):
                            data["items"].append({
                                "description": title, "category": "General",
                                "quantity": float(gen_match.group("qty")),
                                "unit_price": float(gen_match.group("price")), "line_total": total
                            })
        return data

    @staticmethod
    def parse_csv(file_path):
        data = {"vendor": "Unknown", "invoice_number": "Unknown", "invoice_date": "Unknown", "billed_total": 0.0, "items": []}
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            total = 0.0
            for row in reader:
                qty = float(row.get('quantity', 0))
                price = float(row.get('unit_price', 0))
                data["items"].append({
                    "description": row.get('description', 'Unknown Item'),
                    "category": row.get('category', 'General'),
                    "quantity": qty, "unit_price": price, "line_total": qty * price
                })
                total += qty * price
            data["billed_total"] = total
        return data

    @staticmethod
    def parse_json(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
