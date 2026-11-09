from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.auth.utils import login_required, get_current_user, role_required
from app.models import InvoiceModel, ReferencePriceModel, UserModel

views_bp = Blueprint('dashboard_views', __name__)

@views_bp.route('/')
@login_required
def index():
    user = get_current_user()
    stats = InvoiceModel.get_dashboard_statistics()
    return render_template('dashboard.html', user=user, stats=stats)

@views_bp.route('/dashboard')
@login_required
def dashboard():
    return index()

@views_bp.route('/invoices')
@login_required
def invoices_list():
    user = get_current_user()
    query = request.args.get('q', '')
    status = request.args.get('status', '')
    vendor = request.args.get('vendor', '')
    
    invoices = InvoiceModel.list_all(query=query, status=status, vendor=vendor)
    return render_template(
        'invoice_history.html', 
        user=user, 
        invoices=invoices, 
        q=query, 
        current_status=status, 
        current_vendor=vendor
    )

@views_bp.route('/invoices/new')
@login_required
def new_invoice():
    user = get_current_user()
    reference_items = ReferencePriceModel.list_all()
    return render_template('invoice_entry.html', user=user, reference_items=reference_items)

@views_bp.route('/invoices/<int:invoice_id>')
@login_required
def invoice_detail(invoice_id):
    user = get_current_user()
    invoice = InvoiceModel.get_by_id(invoice_id)
    if not invoice:
        flash('Invoice not found', 'error')
        return redirect(url_for('dashboard_views.invoices_list'))

    items = InvoiceModel.get_items(invoice_id)
    anomalies = InvoiceModel.get_anomalies(invoice_id)

    return render_template(
        'invoice_detail.html',
        user=user,
        invoice=invoice,
        items=items,
        anomalies=anomalies
    )

@views_bp.route('/reference-prices')
@login_required
def reference_prices():
    user = get_current_user()
    prices = ReferencePriceModel.list_all()
    return render_template('reference_prices.html', user=user, prices=prices)

@views_bp.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    user = get_current_user()
    users = UserModel.list_all()
    return render_template('admin_users.html', user=user, users=users)
