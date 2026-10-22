from app.core.calculation_engine import verify_invoice_calculations
from app.core.rules import (
    CalculationErrorRule,
    OverbillingRule,
    DuplicateInvoiceRule,
    DuplicateItemRule,
    PriceAnomalyRule,
    TaxAndDiscountRule
)

SEVERITY_WEIGHTS = {
    'CRITICAL': 40,
    'HIGH': 25,
    'MEDIUM': 15,
    'LOW': 5
}

class AnomalyEngine:
    def __init__(self, rules=None):
        if rules is None:
            self.rules = [
                CalculationErrorRule(),
                OverbillingRule(),
                DuplicateInvoiceRule(),
                DuplicateItemRule(),
                PriceAnomalyRule(),
                TaxAndDiscountRule()
            ]
        else:
            self.rules = rules

    def register_rule(self, rule):
        """Allows dynamic registration of custom detection rules (NFR-5.1)."""
        self.rules.append(rule)

    def analyze_invoice(self, invoice_data, context=None):
        """
        Executes full invoice verification and anomaly detection pipeline.
        
        Args:
            invoice_data: dictionary representing invoice and items
            context: dict containing database lookup helpers:
                     - 'ref_finder': callable(desc, category) -> reference row
                     - 'hist_finder': callable(desc, exclude_id) -> list of previous purchases
                     - 'duplicate_invoices': list of matching invoice rows

        Returns:
            dict containing:
                - calculation_results
                - anomalies (list of classified anomalies with severity)
                - risk_score (0-100)
                - risk_level ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
                - status ('NORMAL' or 'SUSPICIOUS')
                - summary (executive text overview)
        """
        if context is None:
            context = {}

        # 1. Verification of Calculations (FR-3, FR-6)
        calc_results = verify_invoice_calculations(invoice_data)

        # 2. Anomaly Detection across all registered rules
        detected_anomalies = []
        for rule in self.rules:
            findings = rule.evaluate(invoice_data, calc_results, context)
            if findings:
                detected_anomalies.extend(findings)

        # 3. Calculate Risk Score and Classification (FR-7.1, FR-7.2)
        total_weight = 0
        severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for anomaly in detected_anomalies:
            sev = anomaly['severity']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            total_weight += SEVERITY_WEIGHTS.get(sev, 10)

        risk_score = min(100.0, float(total_weight))

        if risk_score >= 50 or severity_counts['CRITICAL'] > 0:
            risk_level = 'CRITICAL'
            status = 'SUSPICIOUS'
        elif risk_score >= 25 or severity_counts['HIGH'] > 0:
            risk_level = 'HIGH'
            status = 'SUSPICIOUS'
        elif risk_score > 0:
            risk_level = 'MEDIUM'
            status = 'SUSPICIOUS'
        else:
            risk_level = 'LOW'
            status = 'NORMAL'

        # 4. Generate Executive Summary
        if not detected_anomalies:
            summary = (
                f"Invoice #{invoice_data.get('invoice_number')} from {invoice_data.get('vendor')} "
                f"passed all audit checks. All line item amounts, tax calculations, and unit prices "
                f"align with benchmark references. No duplicates or overbilling detected."
            )
        else:
            summary_parts = [
                f"Audit flagged {len(detected_anomalies)} anomaly/anomalies with {risk_level} risk (Score: {risk_score:.0f}/100)."
            ]
            if calc_results['total_discrepancy'] > 0:
                summary_parts.append(f"Potential overbilling identified: {calc_results['total_discrepancy']:,.2f}.")
            if severity_counts['CRITICAL'] > 0:
                summary_parts.append(f"{severity_counts['CRITICAL']} critical issue(s) require immediate human review.")
            summary = " ".join(summary_parts)

        return {
            'calculation_results': calc_results,
            'anomalies': detected_anomalies,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'status': status,
            'severity_counts': severity_counts,
            'summary': summary
        }
