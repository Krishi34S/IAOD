from flask import Blueprint, request, jsonify
from app.auth.utils import login_required, role_required
from app.models import ReferencePriceModel

ref_prices_api = Blueprint('ref_prices_api', __name__, url_prefix='/api/reference-prices')

@ref_prices_api.route('', methods=['GET'])
@login_required
def list_reference_prices():
    prices = ReferencePriceModel.list_all()
    return jsonify({
        'count': len(prices),
        'reference_prices': [dict(p) for p in prices]
    })

@ref_prices_api.route('', methods=['POST'])
@login_required
@role_required('admin', 'finance_staff')
def create_reference_price():
    data = request.get_json() or {}
    item_name = data.get('item_name')
    category = data.get('category', 'General')
    expected_unit_price = data.get('expected_unit_price')
    tolerance_percent = data.get('tolerance_percent', 15.0)
    unit = data.get('unit', 'unit')

    if not item_name or expected_unit_price is None:
        return jsonify({'error': 'item_name and expected_unit_price are required'}), 400

    try:
        price_val = float(expected_unit_price)
        tol_val = float(tolerance_percent)
        ref_id = ReferencePriceModel.create(item_name, category, price_val, tol_val, unit)
        return jsonify({
            'message': 'Reference price added successfully',
            'reference_id': ref_id
        }), 201
    except Exception as e:
        return jsonify({'error': 'Failed to save reference price', 'details': str(e)}), 400

@ref_prices_api.route('/<int:ref_id>', methods=['PUT'])
@login_required
@role_required('admin', 'finance_staff')
def update_reference_price(ref_id):
    existing = ReferencePriceModel.get_by_id(ref_id)
    if not existing:
        return jsonify({'error': 'Reference price not found'}), 404

    data = request.get_json() or {}
    item_name = data.get('item_name', existing['item_name'])
    category = data.get('category', existing['category'])
    expected_unit_price = float(data.get('expected_unit_price', existing['expected_unit_price']))
    tolerance_percent = float(data.get('tolerance_percent', existing['tolerance_percent']))
    unit = data.get('unit', existing['unit'])

    ReferencePriceModel.update(ref_id, item_name, category, expected_unit_price, tolerance_percent, unit)
    return jsonify({'message': 'Reference price updated successfully'})

@ref_prices_api.route('/<int:ref_id>', methods=['DELETE'])
@login_required
@role_required('admin', 'finance_staff')
def delete_reference_price(ref_id):
    existing = ReferencePriceModel.get_by_id(ref_id)
    if not existing:
        return jsonify({'error': 'Reference price not found'}), 404

    ReferencePriceModel.delete(ref_id)
    return jsonify({'message': 'Reference price deleted successfully'})
