from abc import ABC, abstractmethod

class BaseDetectionRule(ABC):
    """Abstract base class for all anomaly detection rules."""
    
    @abstractmethod
    def evaluate(self, invoice_data, calc_results, context):
        """
        Evaluate the invoice and return a list of anomaly dictionaries:
        [{
            'anomaly_type': str,
            'severity': 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL',
            'item_id': int or None,
            'affected_value': float or None,
            'expected_value': float or None,
            'difference': float or None,
            'explanation': str
        }]
        """
        pass


class CalculationErrorRule(BaseDetectionRule):
    """FR-3.4: Flags arithmetic errors in line items or invoice subtotal."""
    
    def evaluate(self, invoice_data, calc_results, context):
        anomalies = []
        for err in calc_results.get('calculation_errors', []):
            diff = err['difference']
            # If billed line total > expected line total, it's high severity; else medium
            severity = 'HIGH' if diff > 0 else 'MEDIUM'
            anomalies.append({
                'anomaly_type': 'CALCULATION_ERROR',
                'severity': severity,
                'item_id': err.get('item_id'),
                'affected_value': err['billed_line_total'],
                'expected_value': err['expected_line_total'],
                'difference': diff,
                'explanation': err['explanation']
            })
        return anomalies


class OverbillingRule(BaseDetectionRule):
    """FR-4: Flags invoices where billed total exceeds mathematically expected total."""
    
    def evaluate(self, invoice_data, calc_results, context):
        anomalies = []
        diff = calc_results['total_discrepancy']
        billed_total = calc_results['billed_total']
        expected_total = calc_results['expected_total']

        if diff > 0.05:  # Tolerance threshold for floating point rounding
            pct_overbilled = (diff / expected_total * 100.0) if expected_total > 0 else 100.0
            
            if pct_overbilled >= 20.0 or diff >= 10000.0:
                severity = 'CRITICAL'
            elif pct_overbilled >= 5.0 or diff >= 1000.0:
                severity = 'HIGH'
            else:
                severity = 'MEDIUM'

            anomalies.append({
                'anomaly_type': 'OVERBILLING',
                'severity': severity,
                'item_id': None,
                'affected_value': billed_total,
                'expected_value': expected_total,
                'difference': diff,
                'explanation': (
                    f"Possible overbilling detected: Billed total {billed_total:,.2f} exceeds "
                    f"expected total {expected_total:,.2f} by {diff:,.2f} ({pct_overbilled:.1f}% excess)."
                )
            })
        return anomalies


class DuplicateInvoiceRule(BaseDetectionRule):
    """FR-5.1: Checks if this invoice already exists in the database."""
    
    def evaluate(self, invoice_data, calc_results, context):
        anomalies = []
        existing_matches = context.get('duplicate_invoices', [])
        current_id = invoice_data.get('invoice_id')

        for match in existing_matches:
            # If it's another invoice with the same vendor and invoice number
            if current_id and match['invoice_id'] == current_id:
                continue

            anomalies.append({
                'anomaly_type': 'DUPLICATE_INVOICE',
                'severity': 'CRITICAL',
                'item_id': None,
                'affected_value': invoice_data['billed_total'],
                'expected_value': match['billed_total'],
                'difference': round(invoice_data['billed_total'] - match['billed_total'], 2),
                'explanation': (
                    f"Duplicate invoice detected: Invoice #{invoice_data['invoice_number']} for vendor "
                    f"'{invoice_data['vendor']}' already exists in database (Invoice ID #{match['invoice_id']}, "
                    f"dated {match['invoice_date']}, billed amount: {match['billed_total']:,.2f})."
                )
            })
        return anomalies


class DuplicateItemRule(BaseDetectionRule):
    """FR-5.2: Detects duplicated line items within the same invoice."""
    
    def evaluate(self, invoice_data, calc_results, context):
        anomalies = []
        seen = {}
        for idx, item in enumerate(invoice_data.get('items', []), start=1):
            key = item['description'].strip().lower()
            if key in seen:
                prev_idx = seen[key]
                anomalies.append({
                    'anomaly_type': 'DUPLICATE_ITEM',
                    'severity': 'HIGH',
                    'item_id': item.get('item_id'),
                    'affected_value': item['line_total'],
                    'expected_value': 0.0,
                    'difference': item['line_total'],
                    'explanation': (
                        f"Repeated line item '{item['description']}' at position #{idx}. "
                        f"This item was already billed at position #{prev_idx}. Repeated billing of identical items suggests accidental duplication or artificial price inflation."
                    )
                })
            else:
                seen[key] = idx
        return anomalies


class PriceAnomalyRule(BaseDetectionRule):
    """FR-5.3 & FR-5.4: Compares item unit price against reference catalog and historical purchases."""
    
    def evaluate(self, invoice_data, calc_results, context):
        anomalies = []
        ref_finder = context.get('ref_finder')
        hist_finder = context.get('hist_finder')

        for item in invoice_data.get('items', []):
            desc = item['description']
            unit_p = float(item['unit_price'])
            category = item.get('category')

            # 1. Compare against Reference Price Catalog
            ref_match = ref_finder(desc, category) if ref_finder else None
            if ref_match:
                expected_p = float(ref_match['expected_unit_price'])
                tolerance_pct = float(ref_match['tolerance_percent'])
                max_allowed_p = expected_p * (1.0 + tolerance_pct / 100.0)

                if unit_p > max_allowed_p:
                    variance_pct = ((unit_p - expected_p) / expected_p) * 100.0
                    unit_diff = round(unit_p - expected_p, 2)
                    total_excess = round(unit_diff * float(item['quantity']), 2)

                    if variance_pct >= 50.0:
                        severity = 'CRITICAL'
                    elif variance_pct >= 25.0:
                        severity = 'HIGH'
                    else:
                        severity = 'MEDIUM'

                    anomalies.append({
                        'anomaly_type': 'PRICE_ANOMALY',
                        'severity': severity,
                        'item_id': item.get('item_id'),
                        'affected_value': unit_p,
                        'expected_value': expected_p,
                        'difference': total_excess,
                        'explanation': (
                            f"Unusually high price for '{desc}': Billed unit price {unit_p:,.2f} is "
                            f"{variance_pct:.1f}% above the benchmark reference price of {expected_p:,.2f} "
                            f"(tolerance threshold: {tolerance_pct}%). Total excess impact on line item: {total_excess:,.2f}."
                        )
                    })
                    continue  # already flagged via benchmark

            # 2. Compare against Historical Purchase Prices (if no catalog match or catalog passed)
            if hist_finder:
                history = hist_finder(desc, exclude_invoice_id=invoice_data.get('invoice_id'))
                if history and len(history) >= 1:
                    avg_hist_price = sum(h['unit_price'] for h in history) / len(history)
                    if avg_hist_price > 0 and unit_p > avg_hist_price * 1.25: # >25% higher than historical avg
                        variance_pct = ((unit_p - avg_hist_price) / avg_hist_price) * 100.0
                        total_excess = round((unit_p - avg_hist_price) * float(item['quantity']), 2)
                        anomalies.append({
                            'anomaly_type': 'PRICE_ANOMALY',
                            'severity': 'HIGH' if variance_pct >= 50 else 'MEDIUM',
                            'item_id': item.get('item_id'),
                            'affected_value': unit_p,
                            'expected_value': round(avg_hist_price, 2),
                            'difference': total_excess,
                            'explanation': (
                                f"Historical price deviation for '{desc}': Unit price {unit_p:,.2f} is "
                                f"{variance_pct:.1f}% higher than historical purchase average ({avg_hist_price:,.2f} "
                                f"across {len(history)} past purchase(s)). Excess impact: {total_excess:,.2f}."
                            )
                        })

        return anomalies


class TaxAndDiscountRule(BaseDetectionRule):
    """FR-6: Verifies tax calculations and discount bounds."""
    
    def evaluate(self, invoice_data, calc_results, context):
        anomalies = []

        # Tax discrepancy check (FR-6.3)
        tax_diff = calc_results['tax_discrepancy']
        if abs(tax_diff) > 0.05 and calc_results['tax_rate'] > 0:
            anomalies.append({
                'anomaly_type': 'TAX_MISMATCH',
                'severity': 'HIGH' if tax_diff > 100 else 'MEDIUM',
                'item_id': None,
                'affected_value': calc_results['billed_tax'],
                'expected_value': calc_results['expected_tax'],
                'difference': tax_diff,
                'explanation': (
                    f"Tax calculation mismatch: Billed tax amount {calc_results['billed_tax']:,.2f} "
                    f"does not match expected tax {calc_results['expected_tax']:,.2f} computed at {calc_results['tax_rate']}% "
                    f"on taxable base (diff: {tax_diff:+,.2f})."
                )
            })

        # Discount error check (FR-6.2)
        if calc_results.get('discount_error'):
            anomalies.append({
                'anomaly_type': 'DISCOUNT_MISMATCH',
                'severity': 'HIGH',
                'item_id': None,
                'affected_value': calc_results['billed_discount'],
                'expected_value': 0.0,
                'difference': calc_results['billed_discount'],
                'explanation': calc_results['discount_error']
            })

        return anomalies
