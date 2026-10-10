from datetime import datetime

class InvoiceValidationError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors) if isinstance(errors, list) else str(errors))
        self.errors = errors if isinstance(errors, list) else [str(errors)]

def validate_invoice_payload(data):
    """
    Validate the incoming invoice payload against FR-2.3 and FR-2.4.
    Returns sanitized data dict or raises InvoiceValidationError.
    """
    errors = []
    sanitized = {}

    if not isinstance(data, dict):
        raise InvoiceValidationError(["Payload must be a JSON object"])

    # 1. Invoice Number (Required, non-empty string)
    inv_num = data.get('invoice_number')
    if not inv_num or not str(inv_num).strip():
        errors.append("Missing required field: 'invoice_number'")
    else:
        sanitized['invoice_number'] = str(inv_num).strip()

    # 2. Vendor (Required, non-empty string)
    vendor = data.get('vendor')
    if not vendor or not str(vendor).strip():
        errors.append("Missing required field: 'vendor'")
    else:
        sanitized['vendor'] = str(vendor).strip()

    # 3. Invoice Date (Required, valid YYYY-MM-DD or parseable date)
    inv_date = data.get('invoice_date')
    if not inv_date:
        errors.append("Missing required field: 'invoice_date'")
    else:
        try:
            # support various common date formats
            date_str = str(inv_date).strip()
            parsed_date = None
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if parsed_date:
                sanitized['invoice_date'] = parsed_date.strftime("%Y-%m-%d")
            else:
                errors.append(f"Invalid date format for 'invoice_date': '{inv_date}'. Expected YYYY-MM-DD or DD/MM/YYYY")
        except Exception as e:
            errors.append(f"Invalid 'invoice_date': {str(e)}")

    # 4. Numerical Totals
    def parse_float(val, name, default=0.0, allow_negative=False):
        if val is None or str(val).strip() == '':
            return default
        try:
            num = float(str(val).replace(',', '').strip())
            if not allow_negative and num < 0:
                errors.append(f"'{name}' cannot be negative (got {num})")
            return round(num, 2)
        except ValueError:
            errors.append(f"'{name}' must be a valid number (got '{val}')")
            return default

    billed_total = parse_float(data.get('billed_total'), 'billed_total')
    if billed_total <= 0:
        errors.append("Field 'billed_total' must be greater than zero")
    sanitized['billed_total'] = billed_total

    sanitized['billed_subtotal'] = parse_float(data.get('billed_subtotal'), 'billed_subtotal')
    sanitized['tax_rate'] = parse_float(data.get('tax_rate'), 'tax_rate')
    sanitized['tax_amount'] = parse_float(data.get('tax_amount'), 'tax_amount')
    sanitized['discount_amount'] = parse_float(data.get('discount_amount'), 'discount_amount')
    sanitized['raw_file_name'] = data.get('raw_file_name', None)

    # 5. Items (Must be a list with at least 1 item)
    raw_items = data.get('items')
    if not raw_items or not isinstance(raw_items, list) or len(raw_items) == 0:
        errors.append("Invoice must contain at least one line item in 'items'")
    else:
        sanitized_items = []
        for idx, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                errors.append(f"Item #{idx} must be a valid dictionary")
                continue
            
            desc = item.get('description')
            if not desc or not str(desc).strip():
                errors.append(f"Item #{idx} is missing a 'description'")
                continue
            
            qty = parse_float(item.get('quantity'), f"Item #{idx} quantity")
            if qty <= 0:
                errors.append(f"Item #{idx} quantity must be greater than 0")

            unit_price = parse_float(item.get('unit_price'), f"Item #{idx} unit_price")
            
            line_total = item.get('line_total')
            if line_total is None or str(line_total).strip() == '':
                # calculate default if not supplied
                line_total = round(qty * unit_price, 2)
            else:
                line_total = parse_float(line_total, f"Item #{idx} line_total")

            sanitized_items.append({
                'description': str(desc).strip(),
                'category': str(item.get('category', 'General')).strip(),
                'quantity': qty,
                'unit_price': unit_price,
                'line_total': line_total,
                'expected_line_total': round(qty * unit_price, 2)
            })

        sanitized['items'] = sanitized_items

    if errors:
        raise InvoiceValidationError(errors)

    # If subtotal was not provided, default to sum of item line_totals
    if sanitized.get('billed_subtotal', 0.0) <= 0 and sanitized.get('items'):
        sanitized['billed_subtotal'] = round(sum(i['line_total'] for i in sanitized['items']), 2)

    return sanitized
