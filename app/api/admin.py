from flask import Blueprint, request, jsonify
from app.auth.utils import login_required, role_required
from app.models import UserModel

admin_api = Blueprint('admin_api', __name__, url_prefix='/api/admin')

@admin_api.route('/users', methods=['GET'])
@login_required
@role_required('admin')
def list_users():
    users = UserModel.list_all()
    return jsonify({
        'count': len(users),
        'users': [dict(u) for u in users]
    })

@admin_api.route('/users/<int:user_id>/role', methods=['PUT'])
@login_required
@role_required('admin')
def update_user_role(user_id):
    user = UserModel.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}
    new_role = data.get('role', '').strip().lower()

    if new_role not in ('user', 'finance_staff', 'management', 'admin'):
        return jsonify({'error': 'Invalid role. Allowed: user, finance_staff, management, admin'}), 400

    UserModel.update_role(user_id, new_role)
    return jsonify({'message': f"User role updated to '{new_role}' successfully"})
