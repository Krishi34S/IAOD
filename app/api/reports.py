import os
from flask import Blueprint, request, jsonify, send_file, current_app, Response
from app.auth.utils import login_required
from app.models import InvoiceModel
from app.services.report_service import ReportGenerator

reports_api = Blueprint('reports_api', __name__, url_prefix='/api/reports')

@reports_api.route('/<int:invoice_id>/download', methods=['GET'])
@login_required
def download_report(invoice_id):
    """FR-7.4, FR-7.5: Download audit analysis report in PDF, JSON, or CSV."""
    invoice = InvoiceModel.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    items = InvoiceModel.get_items(invoice_id)
    anomalies = InvoiceModel.get_anomalies(invoice_id)
    export_format = request.args.get('format', 'pdf').lower()

    if export_format == 'json':
        data_str = ReportGenerator.export_json_report(invoice, items, anomalies)
        return Response(
            data_str,
            mimetype='application/json',
            headers={'Content-Disposition': f"attachment;filename=IAOD_Audit_Report_{invoice['invoice_number']}.json"}
        )

    elif export_format == 'csv':
        csv_str = ReportGenerator.export_csv_report(invoice, items, anomalies)
        return Response(
            csv_str,
            mimetype='text/csv',
            headers={'Content-Disposition': f"attachment;filename=IAOD_Audit_Report_{invoice['invoice_number']}.csv"}
        )

    else:
        # Default PDF
        reports_dir = current_app.config['REPORTS_FOLDER']
        os.makedirs(reports_dir, exist_ok=True)
        pdf_filename = f"IAOD_Audit_Report_{invoice['invoice_id']}_{invoice['invoice_number'].replace('/', '_')}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_filename)

        ReportGenerator.generate_pdf_report(invoice, items, anomalies, pdf_path)

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_filename
        )
