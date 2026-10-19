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

