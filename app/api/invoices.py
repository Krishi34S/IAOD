import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.auth.utils import login_required, get_current_user, role_required
from app.models import InvoiceModel, ReferencePriceModel
from app.core.validator import validate_invoice_payload, InvoiceValidationError
from app.core.parsers import parse_uploaded_invoice, InvoiceParseError
from app.core.anomaly_engine import AnomalyEngine

invoices_api = Blueprint('invoices_api', __name__, url_prefix='/api/invoices')
engine = AnomalyEngine()

def run_analysis_for_invoice(invoice_id, invoice_dict):
    """Helper to run the anomaly detection engine on an invoice and persist results."""
    # Build database context helpers for rules
    context = {
        'ref_finder': ReferencePriceModel.find_match,
        'hist_finder': InvoiceModel.find_historical_item_prices,
        'duplicate_invoices': InvoiceModel.find_potential_duplicates(
            invoice_dict['vendor'], 
            invoice_dict['invoice_number'], 
            current_invoice_id=invoice_id
        )
    }

    # Run anomaly engine
    analysis_result = engine.analyze_invoice(invoice_dict, context=context)

    # Persist findings back to database
    InvoiceModel.update_analysis_results(
        invoice_id=invoice_id,
        calc_results=analysis_result['calculation_results'],
        anomalies=analysis_result['anomalies'],
        risk_score=analysis_result['risk_score'],
        status=analysis_result['status']
    )

    return analysis_result


@invoices_api.route('', methods=['POST'])
@login_required
def create_invoice():
    """
    FR-2.1, FR-2.2: Upload an invoice file or submit manually entered JSON details.
    Triggers validation (FR-2.3, FR-2.4) and automatically runs initial analysis.
    """
    user = get_current_user()
    
    # Check if this is a file upload (multipart/form-data)
    if 'file' in request.files:
        uploaded_file = request.files['file']
        if not uploaded_file or uploaded_file.filename == '':
            return jsonify({'error': 'No file selected for upload'}), 400

        filename = secure_filename(uploaded_file.filename)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        uploaded_file.save(file_path)

        # Parse file based on extension
        try:
            with open(file_path, 'rb') as f:
                invoice_data = parse_uploaded_invoice(f, filename)
        except (InvoiceParseError, InvoiceValidationError) as e:
            return jsonify({'error': 'Invoice parsing error', 'details': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Unexpected upload error', 'details': str(e)}), 500

    elif request.is_json:
        # Manual entry payload
        try:
            invoice_data = validate_invoice_payload(request.get_json())
        except InvoiceValidationError as e:
            return jsonify({'error': 'Validation error', 'details': e.errors}), 400
    else:
        return jsonify({'error': 'Unsupported Media Type: expected JSON or multipart file'}), 415

    # Save to database
    try:
        invoice_id = InvoiceModel.create(invoice_data, user_id=user['user_id'])
        invoice_data['invoice_id'] = invoice_id
        
        # Attach generated item_ids to invoice items for accurate anomaly association
        saved_items = InvoiceModel.get_items(invoice_id)
        for i, saved_item in enumerate(saved_items):
            if i < len(invoice_data['items']):
                invoice_data['items'][i]['item_id'] = saved_item['item_id']

        # Run analysis immediately (FR-3, FR-4, FR-5, FR-6, FR-7)
        analysis_result = run_analysis_for_invoice(invoice_id, invoice_data)

        return jsonify({
            'message': 'Invoice created and analyzed successfully',
            'invoice_id': invoice_id,
            'status': analysis_result['status'],
            'risk_score': analysis_result['risk_score'],
            'total_anomalies': len(analysis_result['anomalies']),
            'summary': analysis_result['summary']
        }), 201

    except Exception as e:
        return jsonify({'error': 'Failed to save invoice', 'details': str(e)}), 500


@invoices_api.route('', methods=['GET'])
@login_required
def list_invoices():
    """FR-8.2: Search and view previous invoices."""
    query = request.args.get('q')
    status = request.args.get('status')
    vendor = request.args.get('vendor')
    limit = int(request.args.get('limit', 100))

    invoices = InvoiceModel.list_all(query=query, status=status, vendor=vendor, limit=limit)
    return jsonify({
        'count': len(invoices),
        'invoices': [dict(inv) for inv in invoices]
    })


@invoices_api.route('/<int:invoice_id>', methods=['GET'])
@login_required
def get_invoice(invoice_id):
    """View one invoice and its details."""
    invoice = InvoiceModel.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    items = InvoiceModel.get_items(invoice_id)
    anomalies = InvoiceModel.get_anomalies(invoice_id)

    return jsonify({
        'invoice': dict(invoice),
        'items': [dict(i) for i in items],
        'anomalies': [dict(a) for a in anomalies]
    })


@invoices_api.route('/<int:invoice_id>/analyze', methods=['POST'])
@login_required
def analyze_invoice_endpoint(invoice_id):
    """FR-3, FR-4, FR-5: Run or re-run calculation and anomaly checks."""
    invoice = InvoiceModel.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    items = InvoiceModel.get_items(invoice_id)
    invoice_dict = dict(invoice)
    invoice_dict['items'] = [dict(i) for i in items]

    analysis_result = run_analysis_for_invoice(invoice_id, invoice_dict)

    return jsonify({
        'message': 'Analysis complete',
        'invoice_id': invoice_id,
        'status': analysis_result['status'],
        'risk_score': analysis_result['risk_score'],
        'calculation_results': analysis_result['calculation_results'],
        'anomalies': analysis_result['anomalies'],
        'summary': analysis_result['summary']
    })


@invoices_api.route('/<int:invoice_id>/anomalies', methods=['GET'])
@login_required
def get_invoice_anomalies(invoice_id):
    """Retrieve detected anomalies for an invoice."""
    invoice = InvoiceModel.get_by_id(invoice_id)
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    anomalies = InvoiceModel.get_anomalies(invoice_id)
    return jsonify({
        'invoice_id': invoice_id,
        'count': len(anomalies),
        'anomalies': [dict(a) for a in anomalies]
    })
