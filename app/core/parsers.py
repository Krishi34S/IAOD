import json
import csv
import re
from pypdf import PdfReader
from app.core.validator import InvoiceValidationError, validate_invoice_payload

class InvoiceParseError(Exception):
    pass

def parse_invoice_json(content_or_stream):
    try:
        if hasattr(content_or_stream, 'read'):
            raw = content_or_stream.read()
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8', errors='replace')
            data = json.loads(raw)
        elif isinstance(content_or_stream, str):
            data = json.loads(content_or_stream)
        else:
            raise InvoiceParseError("Unsupported input type for JSON parser")
        return validate_invoice_payload(data)
    except json.JSONDecodeError as e:
        raise InvoiceParseError(f"Malformed JSON: {str(e)}")

def parse_invoice_csv(content_or_stream):
    try:
        if hasattr(content_or_stream, 'read'):
            raw = content_or_stream.read()
            if isinstance(raw, bytes):
                raw = raw.decode('utf-8', errors='replace')
        else:
            raw = str(content_or_stream)

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if not lines:
            raise InvoiceParseError("CSV content is empty")

        first_line = lines[0].lower()
        data = {
            'invoice_number': '', 'vendor': '', 'invoice_date': '',
            'billed_total': 0.0, 'billed_subtotal': 0.0,
            'tax_rate': 0.0, 'tax_amount': 0.0, 'discount_amount': 0.0, 'items': []
        }
        if 'description' in first_line and ('quantity' in first_line or 'qty' in first_line):
            reader = csv.DictReader(lines)
            for row in reader:
                norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                if not data['invoice_number']:
                    data['invoice_number'] = norm_row.get('invoice_number', norm_row.get('invoice_no', ''))
                if not data['vendor']:
                    data['vendor'] = norm_row.get('vendor', norm_row.get('vendor_name', ''))
                if not data['invoice_date']:
                    data['invoice_date'] = norm_row.get('invoice_date', norm_row.get('date', ''))
                if not data['billed_total'] and 'billed_total' in norm_row:
                    try: data['billed_total'] = float(norm_row['billed_total'])
                    except ValueError: pass
                if not data['tax_rate'] and 'tax_rate' in norm_row:
                    try: data['tax_rate'] = float(norm_row['tax_rate'])
                    except ValueError: pass
                if not data['discount_amount'] and 'discount_amount' in norm_row:
                    try: data['discount_amount'] = float(norm_row['discount_amount'])
                    except ValueError: pass
                desc = norm_row.get('description', norm_row.get('item', ''))
                if desc:
                    qty = float(norm_row.get('quantity', norm_row.get('qty', 1)))
                    unit_p = float(norm_row.get('unit_price', norm_row.get('price', 0)))
                    line_t = float(norm_row.get('line_total', norm_row.get('total', qty * unit_p)))
                    data['items'].append({
                        'description': desc, 'category': norm_row.get('category', 'General'),
                        'quantity': qty, 'unit_price': unit_p, 'line_total': line_t
                    })
            if not data['billed_total'] and data['items']:
                data['billed_total'] = sum(i['line_total'] for i in data['items'])
            return validate_invoice_payload(data)
        else:
            items_section = False
            items_header = []
            for line in lines:
                parts = [p.strip() for p in list(csv.reader([line]))[0]]
                if not parts: continue
                if '[items]' in parts[0].lower() or 'items:' in parts[0].lower():
                    items_section = True
                    continue
                if not items_section:
                    key = parts[0].lower().replace('_', ' ').replace('-', ' ').strip()
                    val = parts[1].strip() if len(parts) > 1 else ''
                    if 'invoice number' in key or 'invoice no' in key or 'invoice #' in key: data['invoice_number'] = val
                    elif 'vendor' in key or 'supplier' in key: data['vendor'] = val
                    elif 'date' in key: data['invoice_date'] = val
                    elif 'tax rate' in key or 'tax %' in key:
                        try: data['tax_rate'] = float(val.replace('%', ''))
                        except ValueError: pass
                    elif 'tax' in key:
                        try: data['tax_amount'] = float(val)
                        except ValueError: pass
                    elif 'discount' in key:
                        try: data['discount_amount'] = float(val)
                        except ValueError: pass
                    elif 'total' in key:
                        try: data['billed_total'] = float(val)
                        except ValueError: pass
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
                                'description': desc, 'category': row_dict.get('category', 'General'),
                                'quantity': qty, 'unit_price': unit_p, 'line_total': line_t
                            })
            if not data['billed_total'] and data['items']:
                data['billed_total'] = sum(i['line_total'] for i in data['items'])
            return validate_invoice_payload(data)
    except Exception as e:
        if isinstance(e, InvoiceValidationError): raise
        raise InvoiceParseError(f"Failed to parse CSV invoice: {str(e)}")

def parse_invoice_pdf(file_stream):
    try:
        reader = PdfReader(file_stream)
        full_text = "\n".join((p.extract_text() or "") for p in reader.pages)
        if not full_text.strip():
            raise InvoiceParseError("No readable text found in PDF document")
        data = {
            'invoice_number': 'INV-AUTO-DETECTED', 'vendor': 'Extracted Vendor', 'invoice_date': '2026-01-01',
            'billed_total': 0.0, 'tax_rate': 0.0, 'tax_amount': 0.0, 'discount_amount': 0.0, 'items': []
        }
        inv_m = re.search(r'(?:Invoice\s*(?:Number|No\.?|#)\s*[:\-]?\s*)([A-Za-z0-9\-_/]+)', full_text, re.IGNORECASE)
        if inv_m: data['invoice_number'] = inv_m.group(1).strip()
        ven_m = re.search(r'(?:Vendor|Supplier|From)\s*[:\-]?\s*([^\n\r]+)', full_text, re.IGNORECASE)
        if ven_m: data['vendor'] = ven_m.group(1).strip()
        dt_m = re.search(r'(?:Date|Invoice Date)\s*[:\-]?\s*([0-9]{4}[-/][0-9]{2}[-/][0-9]{2}|[0-9]{2}[-/][0-9]{2}[-/][0-9]{4})', full_text, re.IGNORECASE)
        if dt_m: data['invoice_date'] = dt_m.group(1).strip()
        tot_m = re.search(r'(?:Total|Grand Total|Billed Total)\s*[:\-]?\s*(?:[\$₹€£]|Rs\.?)?\s*([0-9,]+\.?[0-9]*)', full_text, re.IGNORECASE)
        if tot_m: data['billed_total'] = float(tot_m.group(1).replace(',', ''))
        item_re = re.compile(r'([A-Za-z0-9\s\-_.,()]+?)\s+([0-9]+(?:\.[0-9]+)?)\s+([0-9,]+(?:\.[0-9]+)?)\s+([0-9,]+(?:\.[0-9]+)?)$', re.MULTILINE)
        for m in item_re.finditer(full_text):
            desc = m.group(1).strip()
            if any(h in desc.lower() for h in ['description', 'subtotal', 'total', 'tax', 'discount', 'item']): continue
            data['items'].append({'description': desc, 'category': 'General', 'quantity': float(m.group(2)),
                                  'unit_price': float(m.group(3).replace(',', '')), 'line_total': float(m.group(4).replace(',', ''))})
        return validate_invoice_payload(data)
    except Exception as e:
        if isinstance(e, InvoiceValidationError): raise
        raise InvoiceParseError(f"Failed to parse PDF invoice: {str(e)}")

def parse_uploaded_invoice(file_storage, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext == 'json': data = parse_invoice_json(file_storage)
    elif ext in ('csv', 'txt'): data = parse_invoice_csv(file_storage)
    elif ext == 'pdf': data = parse_invoice_pdf(file_storage)
    else: raise InvoiceParseError(f"Unsupported file extension: .{ext}")
    data['raw_file_name'] = filename
    return data
