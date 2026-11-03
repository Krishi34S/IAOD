from flask import Blueprint, jsonify
from app.auth.utils import login_required
from app.models import InvoiceModel

dashboard_api = Blueprint('dashboard_api', __name__, url_prefix='/api/dashboard')

@dashboard_api.route('/summary', methods=['GET'])
@login_required
def get_dashboard_summary():
    """FR-8.3, FR-8.4: Retrieve invoice and anomaly summary statistics."""
    stats = InvoiceModel.get_dashboard_statistics()
    return jsonify(stats)
