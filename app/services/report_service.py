import os
import json
import csv
import io
from datetime import datetime
from pathlib import Path
from flask import current_app

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class ReportGenerator:
    @staticmethod
    def generate_pdf_report(invoice, items, anomalies, output_path):
        """Generate a professional PDF audit report using ReportLab."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#1E293B')
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748B')
        )
        h2_style = ParagraphStyle(
            'SectionH2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#334155')
        )
        cell_bold = ParagraphStyle(
            'CellBold',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("INVOICE ANOMALY & OVERBILLING AUDIT REPORT", title_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | System: IAOD 1.0", subtitle_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

        # 2. Status & Risk Badge
        status = invoice['status']
        risk_score = invoice['risk_score'] or 0.0
        status_color = colors.HexColor('#EF4444') if status == 'SUSPICIOUS' else colors.HexColor('#10B981')
        
        status_data = [
            [
                Paragraph("<b>Audit Status:</b>", body_style),
                Paragraph(f"<font color='{status_color.hexval()}'><b>{status}</b></font>", body_style),
                Paragraph("<b>Risk Score:</b>", body_style),
                Paragraph(f"<b>{risk_score:.0f} / 100</b>", body_style),
                Paragraph("<b>Total Anomalies:</b>", body_style),
                Paragraph(f"<b>{len(anomalies)}</b>", body_style)
            ]
        ]
        status_table = Table(status_data, colWidths=[80, 90, 80, 80, 90, 80])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(status_table)
        story.append(Spacer(1, 12))

        # 3. Invoice Metadata
        story.append(Paragraph("1. Invoice Details", h2_style))
        meta_data = [
            [Paragraph("<b>Invoice Number:</b>", body_style), Paragraph(str(invoice['invoice_number']), body_style),
             Paragraph("<b>Vendor Name:</b>", body_style), Paragraph(str(invoice['vendor']), body_style)],
            [Paragraph("<b>Invoice Date:</b>", body_style), Paragraph(str(invoice['invoice_date']), body_style),
             Paragraph("<b>Submitter:</b>", body_style), Paragraph(str(invoice.get('submitter_name', 'System')), body_style)]
        ]
        meta_table = Table(meta_data, colWidths=[110, 150, 110, 170])
        meta_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # 4. Financial Reconciliation Summary
        story.append(Paragraph("2. Financial Reconciliation & Calculation Check", h2_style))
        billed_tot = float(invoice['billed_total'])
        exp_tot = float(invoice['expected_total'] or invoice['billed_total'])
        diff_tot = round(billed_tot - exp_tot, 2)
        
        diff_color = colors.HexColor('#DC2626') if diff_tot > 0 else (colors.HexColor('#16A34A') if diff_tot == 0 else colors.HexColor('#2563EB'))

        fin_data = [
            [Paragraph("<b>Metric</b>", cell_bold), Paragraph("<b>Billed Value</b>", cell_bold), Paragraph("<b>Expected (Recalculated)</b>", cell_bold), Paragraph("<b>Discrepancy</b>", cell_bold)],
            [Paragraph("Subtotal", body_style), f"{float(invoice['billed_subtotal'] or 0):,.2f}", f"{float(invoice['expected_subtotal'] or 0):,.2f}", f"{float((invoice['billed_subtotal'] or 0) - (invoice['expected_subtotal'] or 0)):+,.2f}"],
            [Paragraph("Tax", body_style), f"{float(invoice['tax_amount'] or 0):,.2f}", f"{float(invoice['expected_tax'] or 0):,.2f}", f"{float((invoice['tax_amount'] or 0) - (invoice['expected_tax'] or 0)):+,.2f}"],
            [Paragraph("Discount", body_style), f"{float(invoice['discount_amount'] or 0):,.2f}", f"{float(invoice['discount_amount'] or 0):,.2f}", "0.00"],
            [Paragraph("<b>Total Invoice Amount</b>", cell_bold), 
             Paragraph(f"<b>{billed_tot:,.2f}</b>", cell_bold), 
             Paragraph(f"<b>{exp_tot:,.2f}</b>", cell_bold), 
             Paragraph(f"<font color='{diff_color.hexval()}'><b>{diff_tot:+,.2f}</b></font>", cell_bold)]
        ]
        fin_table = Table(fin_data, colWidths=[150, 120, 140, 130])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8FAFC'))
        ]))
        story.append(fin_table)
        story.append(Spacer(1, 14))

        # 5. Detected Anomalies
        story.append(Paragraph(f"3. Detected Anomalies & Discrepancies ({len(anomalies)})", h2_style))
        if not anomalies:
            story.append(Paragraph("<i>No anomalies or calculation errors detected. Invoice passed all validation rules.</i>", body_style))
        else:
            anomaly_data = [
                [Paragraph("<b>Type</b>", cell_bold), 
                 Paragraph("<b>Severity</b>", cell_bold), 
                 Paragraph("<b>Discrepancy</b>", cell_bold), 
                 Paragraph("<b>Finding & Explanation</b>", cell_bold)]
            ]
            for a in anomalies:
                sev = a['severity']
                sev_color = '#DC2626' if sev == 'CRITICAL' else ('#EA580C' if sev == 'HIGH' else ('#D97706' if sev == 'MEDIUM' else '#2563EB'))
                diff_val = f"{float(a['difference']):+,.2f}" if a['difference'] is not None else "N/A"
                anomaly_data.append([
                    Paragraph(f"<b>{a['anomaly_type']}</b>", body_style),
                    Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", body_style),
                    Paragraph(diff_val, body_style),
                    Paragraph(a['explanation'], body_style)
                ])

            anom_table = Table(anomaly_data, colWidths=[110, 65, 75, 290])
            anom_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEE2E2')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FECACA')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(anom_table)

        story.append(Spacer(1, 14))

        # 6. Itemized Breakdown
        story.append(Paragraph("4. Line Items Audit", h2_style))
        items_data = [
            [Paragraph("<b>#</b>", cell_bold),
             Paragraph("<b>Description</b>", cell_bold),
             Paragraph("<b>Qty</b>", cell_bold),
             Paragraph("<b>Unit Price</b>", cell_bold),
             Paragraph("<b>Billed Total</b>", cell_bold),
             Paragraph("<b>Expected</b>", cell_bold)]
        ]
        for idx, it in enumerate(items, start=1):
            exp_lt = float(it['expected_line_total'])
            billed_lt = float(it['line_total'])
            is_mismatch = abs(billed_lt - exp_lt) > 0.05
            row_color = colors.HexColor('#FEF2F2') if is_mismatch else colors.white
            items_data.append([
                str(idx),
                Paragraph(it['description'], body_style),
                f"{float(it['quantity']):.1f}",
                f"{float(it['unit_price']):,.2f}",
                f"{billed_lt:,.2f}",
                f"{exp_lt:,.2f}"
            ])

        items_table = Table(items_data, colWidths=[25, 215, 45, 80, 85, 90])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 20))

        # 7. Audit Sign-off Note
        story.append(KeepTogether([
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94A3B8'), spaceAfter=8),
            Paragraph(
                "<b>Audit Sign-off Note:</b> This report is generated automatically by the Invoice Anomaly & "
                "Overbilling Detector (IAOD) using predefined rule engines. In accordance with system design constraints, "
                "flagged anomalies serve as warnings for human review by authorized Finance Staff and do not constitute an "
                "automatic rejection or payment decision.",
                subtitle_style
            )
        ]))

        doc.build(story)
        return output_path

    @staticmethod
    def export_json_report(invoice, items, anomalies):
        return json.dumps({
            'invoice': dict(invoice),
            'items': [dict(i) for i in items],
            'anomalies': [dict(a) for a in anomalies],
            'exported_at': datetime.now().isoformat()
        }, indent=2, default=str)

    @staticmethod
    def export_csv_report(invoice, items, anomalies):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['INVOICE AUDIT REPORT', f"Invoice #{invoice['invoice_number']}", f"Vendor: {invoice['vendor']}"])
        writer.writerow(['Status', invoice['status'], 'Risk Score', invoice['risk_score']])
        writer.writerow(['Billed Total', invoice['billed_total'], 'Expected Total', invoice['expected_total'], 'Discrepancy', invoice['total_discrepancy']])
        writer.writerow([])
        writer.writerow(['ANOMALIES'])
        writer.writerow(['Type', 'Severity', 'Discrepancy', 'Explanation'])
        for a in anomalies:
            writer.writerow([a['anomaly_type'], a['severity'], a['difference'], a['explanation']])
        writer.writerow([])
        writer.writerow(['LINE ITEMS'])
        writer.writerow(['Description', 'Category', 'Quantity', 'Unit Price', 'Billed Line Total', 'Expected Line Total'])
        for it in items:
            writer.writerow([it['description'], it['category'], it['quantity'], it['unit_price'], it['line_total'], it['expected_line_total']])
        return output.getvalue()
