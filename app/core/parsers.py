import csv
import io
import json
import os
import re
from datetime import date

import pdfplumber

from app.core.validator import InvoiceValidationError, validate_invoice_payload


class InvoiceParseError(Exception):
    pass


class InvoiceParser:
    @staticmethod
    def parse(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return InvoiceParser.parse_pdf(file_path)
        elif ext in ('.csv', '.txt'):
            return InvoiceParser.parse_csv(file_path)
        elif ext == '.json':
            return InvoiceParser.parse_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _read_text_input(file_or_content):
        if isinstance(file_or_content, (str, os.PathLike)) and os.path.exists(str(file_or_content)):
            with open(file_or_content, mode='r', encoding='utf-8', errors='replace') as f:
                return f.read()
        if hasattr(file_or_content, 'read'):
            raw = file_or_content.read()
            return raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else str(raw)
        return str(file_or_content)

    @staticmethod
    def parse_pdf(file_path_or_stream):
        data = {
            "vendor": "Unknown",
            "invoice_number": "Unknown",
            "invoice_date": "Unknown",
            "billed_total": 0.0,
            "tax_rate": 0.0,
            "tax_amount": 0.0,
            "discount_amount": 0.0,
            "items": []
        }

        # Regex patterns for Header Fields (e-commerce + generic fallbacks)
        vendor_pattern = re.compile(r"Sold By:\s*(.+?)(?:,|$)", re.IGNORECASE)
        generic_vendor_pattern = re.compile(r"(?:Vendor|Supplier|From|Billed By)\s*[:\-]\s*([^\n\r]+)", re.IGNORECASE)

        invoice_num_pattern = re.compile(r"(?:Invoice Number\s*#|Original Invoice Number:)\s*([A-Z0-9\-_/]+)", re.IGNORECASE)
        generic_inv_num_pattern = re.compile(r"(?:Invoice\s*(?:Number|No\.?|#)\s*[:\-]?\s*)([A-Za-z0-9\-_/]+)", re.IGNORECASE)

        date_pattern = re.compile(r"Invoice Date:\s*([\d\-/]+)", re.IGNORECASE)
        generic_date_pattern = re.compile(
            r"(?:Date|Invoice Date)\s*[:\-]?\s*([0-9]{4}[-/][0-9]{2}[-/][0-9]{2}|[0-9]{2}[-/][0-9]{2}[-/][0-9]{4})",
            re.IGNORECASE
        )

        # Matches Grand Total across spaces or newlines, ignoring currency symbols
        grand_total_pattern = re.compile(r"Grand Total[\s\r\n]*(?:₹|Rs\.?)?\s*([\d,]+\.\d{2})", re.IGNORECASE)
        generic_total_pattern = re.compile(
            r"(?:Total|Grand Total|Billed Total|Amount Due)\s*[:\-]?\s*(?:[\$₹€£]|Rs\.?)?\s*([0-9,]+\.?[0-9]*)",
            re.IGNORECASE
        )
        tax_pattern = re.compile(
            r"(?:Tax|GST|VAT)\s*(?:\(([0-9.]+)%\))?\s*[:\-]?\s*(?:[\$₹€£]|Rs\.?)?\s*([0-9,]+\.?[0-9]*)",
            re.IGNORECASE
        )
        discount_pattern = re.compile(
            r"(?:Discount)\s*[:\-]?\s*(?:[\$₹€£]|Rs\.?)?\s*([0-9,]+\.?[0-9]*)",
            re.IGNORECASE
        )

        # Regex pattern for dense e-commerce layouts (Flipkart)
        # Supports both IGST format (1 tax column) and CGST/SGST format (2 tax columns)
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

        # Generic fallback pattern
        generic_item_pattern = re.compile(
            r"^(?P<title>.+?)\s+"
            r"(?P<qty>\d+(?:\.\d+)?)\s+"
            r"(?:[\$₹€£]|Rs\.?)?\s*(?P<price>\d+(?:,\d{3})*(?:\.\d{1,2})?)\s+"
            r"(?:[\$₹€£]|Rs\.?)?\s*(?P<total>\d+(?:,\d{3})*(?:\.\d{1,2})?)$"
        )

        try:
            with pdfplumber.open(file_path_or_stream) as pdf:
                found_grand_total = False

                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue

                    # Scrape metadata
                    if data["vendor"] == "Unknown":
                        v_match = vendor_pattern.search(text) or generic_vendor_pattern.search(text)
                        if v_match:
                            data["vendor"] = v_match.group(1).strip()

                    if data["invoice_number"] == "Unknown":
                        inv_match = invoice_num_pattern.search(text) or generic_inv_num_pattern.search(text)
                        if inv_match:
                            data["invoice_number"] = inv_match.group(1).strip()

                    if data["invoice_date"] == "Unknown":
                        d_match = date_pattern.search(text) or generic_date_pattern.search(text)
                        if d_match:
                            data["invoice_date"] = d_match.group(1).strip()

                    if not found_grand_total:
                        gt_match = grand_total_pattern.search(text) or generic_total_pattern.search(text)
                        if gt_match:
                            data["billed_total"] = float(gt_match.group(1).replace(',', ''))
                            found_grand_total = True

                    if data["tax_amount"] == 0.0:
                        t_match = tax_pattern.search(text)
                        if t_match:
                            if t_match.group(1):
                                try:
                                    data["tax_rate"] = float(t_match.group(1))
                                except ValueError:
                                    pass
                            if t_match.group(2):
                                try:
                                    data["tax_amount"] = float(t_match.group(2).replace(',', ''))
                                except ValueError:
                                    pass

                    if data["discount_amount"] == 0.0:
                        disc_match = discount_pattern.search(text)
                        if disc_match:
                            try:
                                data["discount_amount"] = float(disc_match.group(1).replace(',', ''))
                            except ValueError:
                                pass

                    # Parse Line Items
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # Skip aggregation lines that look like items
                        if line.startswith("Total") or line.startswith("Shipping") or line.startswith("Grand Total"):
                            continue

                        # 1. Try e-commerce dense pattern (Flipkart)
                        ecom_match = ecommerce_item_pattern.match(line)
                        if ecom_match:
                            title = ecom_match.group("title").strip()
                            qty = float(ecom_match.group("qty"))
                            total = float(ecom_match.group("total"))

                            # Prevent duplication from bundled Credit Notes / Tax Invoices in same PDF
                            if not any(i["description"] == title and i["line_total"] == total for i in data["items"]):
                                data["items"].append({
                                    "description": title,
                                    "category": "General",
                                    "quantity": qty,
                                    "unit_price": round(total / qty, 2) if qty > 0 else 0.0,  # Derive actual unit price to pass math checks
                                    "line_total": total
                                })
                            continue

                        # 2. Try generic pattern fallback
                        gen_match = generic_item_pattern.match(line)
                        if gen_match:
                            if "page" in line.lower() or "date" in line.lower():
                                continue

                            title = gen_match.group("title").strip()
                            if any(h in title.lower() for h in ['description', 'subtotal', 'total', 'tax', 'discount']):
                                continue

                            qty = float(gen_match.group("qty"))
                            price = float(gen_match.group("price").replace(',', ''))
                            total = float(gen_match.group("total").replace(',', ''))

                            if not any(i["description"] == title and i["line_total"] == total for i in data["items"]):
                                data["items"].append({
                                    "description": title,
                                    "category": "General",
                                    "quantity": qty,
                                    "unit_price": price,
                                    "line_total": total
                                })

        except Exception as e:
            raise InvoiceParseError(f"Failed to parse PDF invoice: {str(e)}")

        if data["invoice_date"] == "Unknown":
            data["invoice_date"] = date.today().strftime("%Y-%m-%d")

        if data["billed_total"] == 0.0 and data["items"]:
            data["billed_total"] = round(sum(i["line_total"] for i in data["items"]), 2)

        return data

    @staticmethod
    def parse_csv(file_path_or_stream):
        data = {
            "vendor": "Unknown",
            "invoice_number": "Unknown",
            "invoice_date": date.today().strftime("%Y-%m-%d"),
            "billed_total": 0.0,
            "tax_rate": 0.0,
            "tax_amount": 0.0,
            "discount_amount": 0.0,
            "items": []
        }
        try:
            raw = InvoiceParser._read_text_input(file_path_or_stream)
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            if not lines:
                raise InvoiceParseError("CSV content is empty")

            first_line = lines[0].lower()
            if 'description' in first_line and ('quantity' in first_line or 'qty' in first_line):
                reader = csv.DictReader(lines)
                total = 0.0
                explicit_total = None
                for row in reader:
                    norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                    if data["invoice_number"] == "Unknown" and norm_row.get("invoice_number", norm_row.get("invoice_no")):
                        data["invoice_number"] = norm_row.get("invoice_number", norm_row.get("invoice_no"))
                    if data["vendor"] == "Unknown" and norm_row.get("vendor", norm_row.get("vendor_name")):
                        data["vendor"] = norm_row.get("vendor", norm_row.get("vendor_name"))
                    if norm_row.get("invoice_date", norm_row.get("date")):
                        data["invoice_date"] = norm_row.get("invoice_date", norm_row.get("date"))
                    if explicit_total is None and norm_row.get("billed_total"):
                        try:
                            explicit_total = float(norm_row["billed_total"])
                        except ValueError:
                            pass
                    if data["tax_rate"] == 0.0 and norm_row.get("tax_rate"):
                        try:
                            data["tax_rate"] = float(norm_row["tax_rate"])
                        except ValueError:
                            pass
                    if data["discount_amount"] == 0.0 and norm_row.get("discount_amount"):
                        try:
                            data["discount_amount"] = float(norm_row["discount_amount"])
                        except ValueError:
                            pass

                    desc = norm_row.get("description", norm_row.get("item", "Unknown Item"))
                    qty = float(norm_row.get("quantity", norm_row.get("qty", 0)))
                    price = float(norm_row.get("unit_price", norm_row.get("price", 0)))
                    line_total = float(norm_row.get("line_total", norm_row.get("total", qty * price)))
                    data["items"].append({
                        "description": desc,
                        "category": norm_row.get("category", "General"),
                        "quantity": qty,
                        "unit_price": price,
                        "line_total": line_total
                    })
                    total += line_total

                data["billed_total"] = explicit_total if explicit_total is not None else round(total, 2)
            else:
                items_section = False
                items_header = []
                for line in lines:
                    parts = [p.strip() for p in list(csv.reader([line]))[0]]
                    if not parts:
                        continue
                    if '[items]' in parts[0].lower() or 'items:' in parts[0].lower():
                        items_section = True
                        continue
                    if not items_section:
                        key = parts[0].lower().replace('_', ' ').replace('-', ' ').strip()
                        val = parts[1].strip() if len(parts) > 1 else ''
                        if 'invoice number' in key or 'invoice no' in key or 'invoice #' in key:
                            data['invoice_number'] = val
                        elif 'vendor' in key or 'supplier' in key:
                            data['vendor'] = val
                        elif 'date' in key:
                            data['invoice_date'] = val
                        elif 'tax rate' in key or 'tax %' in key:
                            try:
                                data['tax_rate'] = float(val.replace('%', ''))
                            except ValueError:
                                pass
                        elif 'tax amount' in key or 'tax' in key:
                            try:
                                data['tax_amount'] = float(val)
                            except ValueError:
                                pass
                        elif 'discount' in key:
                            try:
                                data['discount_amount'] = float(val)
                            except ValueError:
                                pass
                        elif 'total' in key:
                            try:
                                data['billed_total'] = float(val)
                            except ValueError:
                                pass
                    else:
                        if not items_header:
                            items_header = [p.lower() for p in parts]
                        else:
                            row_dict = dict(zip(items_header, parts))
                            desc = row_dict.get('description', row_dict.get('item', ''))
                            if desc:
                                qty = float(row_dict.get('quantity', row_dict.get('qty', 1)))
                                unit_p = float(row_dict.get('unit_price', row_dict.get('price', 0)))
                                line_t = float(row_dict.get('line_total', row_dict.get('total', qty * unit_p)))
                                data['items'].append({
                                    'description': desc,
                                    'category': row_dict.get('category', 'General'),
                                    'quantity': qty,
                                    'unit_price': unit_p,
                                    'line_total': line_t
                                })

                if not data['billed_total'] and data['items']:
                    data['billed_total'] = round(sum(i['line_total'] for i in data['items']), 2)
        except Exception as e:
            if isinstance(e, InvoiceParseError):
                raise
            raise InvoiceParseError(f"Failed to parse CSV invoice: {str(e)}")
        return data

    @staticmethod
    def parse_json(file_path_or_stream):
        try:
            raw = InvoiceParser._read_text_input(file_path_or_stream)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise InvoiceParseError(f"Malformed JSON: {str(e)}")
        except Exception as e:
            raise InvoiceParseError(f"Failed to parse JSON invoice: {str(e)}")


def parse_invoice_json(content_or_stream):
    return validate_invoice_payload(InvoiceParser.parse_json(content_or_stream))


def parse_invoice_csv(content_or_stream):
    return validate_invoice_payload(InvoiceParser.parse_csv(content_or_stream))


def parse_invoice_pdf(file_path_or_stream):
    return validate_invoice_payload(InvoiceParser.parse_pdf(file_path_or_stream))


def parse_uploaded_invoice(file_path_or_stream, filename):
    """Dispatcher for uploaded invoice files."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext == 'json':
        data = parse_invoice_json(file_path_or_stream)
    elif ext in ('csv', 'txt'):
        data = parse_invoice_csv(file_path_or_stream)
    elif ext == 'pdf':
        data = parse_invoice_pdf(file_path_or_stream)
    else:
        raise InvoiceParseError(f"Unsupported file extension: .{ext}. Allowed: .json, .csv, .pdf, .txt")

    data['raw_file_name'] = filename
    return data
