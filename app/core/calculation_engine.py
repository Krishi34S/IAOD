def verify_invoice_calculations(invoice_dict):
    """
    Verifies mathematical integrity of the invoice according to FR-3 and FR-6.
    
    Returns:
        dict containing:
            - items_verified: list of items with expected_line_total, discrepancy, has_error
            - expected_subtotal: float
            - expected_tax: float
            - expected_discount: float
            - expected_total: float
            - billed_subtotal: float
            - billed_total: float
            - subtotal_discrepancy: float
            - tax_discrepancy: float
            - total_discrepancy: float (positive means billed > expected, i.e. overbilled)
            - calculation_errors: list of error descriptors
    """
    items = invoice_dict.get('items', [])
    items_verified = []
    expected_subtotal = 0.0
    calculation_errors = []

    # 1. Verify line item calculations (FR-3.1)
    for idx, item in enumerate(items, start=1):
        qty = float(item['quantity'])
        unit_price = float(item['unit_price'])
        billed_line_total = float(item['line_total'])
        
        expected_line_total = round(qty * unit_price, 2)
        expected_subtotal += expected_line_total
        
        item_diff = round(billed_line_total - expected_line_total, 2)
        has_error = abs(item_diff) > 0.05  # 5 cents rounding tolerance

        verified_item = dict(item)
        verified_item['expected_line_total'] = expected_line_total
        verified_item['discrepancy'] = item_diff
        verified_item['has_error'] = has_error
        items_verified.append(verified_item)

        if has_error:
            calculation_errors.append({
                'type': 'LINE_ITEM_CALCULATION_ERROR',
                'item_index': idx,
                'description': item['description'],
                'quantity': qty,
                'unit_price': unit_price,
                'billed_line_total': billed_line_total,
                'expected_line_total': expected_line_total,
                'difference': item_diff,
                'explanation': f"Item '{item['description']}': Billed line total {billed_line_total:,.2f} does not match Quantity ({qty}) × Unit Price ({unit_price:,.2f}) = {expected_line_total:,.2f} (diff: {item_diff:+,.2f})"
            })

    expected_subtotal = round(expected_subtotal, 2)
    billed_subtotal = float(invoice_dict.get('billed_subtotal') or expected_subtotal)
    subtotal_discrepancy = round(billed_subtotal - expected_subtotal, 2)

    # 2. Verify Discount (FR-6.2)
    billed_discount = float(invoice_dict.get('discount_amount', 0.0))
    discount_error = None
    if billed_discount < 0:
        discount_error = "Discount cannot be a negative amount."
    elif billed_discount > expected_subtotal:
        discount_error = f"Discount ({billed_discount:,.2f}) exceeds the subtotal ({expected_subtotal:,.2f})."

    # 3. Verify Tax (FR-6.1)
    tax_rate = float(invoice_dict.get('tax_rate', 0.0))
    billed_tax = float(invoice_dict.get('tax_amount', 0.0))
    taxable_base = max(0.0, expected_subtotal)

    if tax_rate > 0:
        expected_tax = round(taxable_base * (tax_rate / 100.0), 2)
    elif billed_tax > 0 and taxable_base > 0:
        # If no rate provided but tax amount provided, infer rate and keep billed
        expected_tax = billed_tax
    else:
        expected_tax = 0.0

    tax_discrepancy = round(billed_tax - expected_tax, 2)

    # 4. Calculate Expected Total (FR-3.2)
    expected_total = round(expected_subtotal - billed_discount + expected_tax, 2)
    billed_total = float(invoice_dict['billed_total'])
    total_discrepancy = round(billed_total - expected_total, 2)

    return {
        'items_verified': items_verified,
        'billed_subtotal': billed_subtotal,
        'expected_subtotal': expected_subtotal,
        'subtotal_discrepancy': subtotal_discrepancy,
        'tax_rate': tax_rate,
        'billed_tax': billed_tax,
        'expected_tax': expected_tax,
        'tax_discrepancy': tax_discrepancy,
        'billed_discount': billed_discount,
        'discount_error': discount_error,
        'billed_total': billed_total,
        'expected_total': expected_total,
        'total_discrepancy': total_discrepancy,
        'calculation_errors': calculation_errors
    }
