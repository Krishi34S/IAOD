from functools import wraps
from flask import session, request, jsonify, redirect, url_for, g
from app.models import UserModel

def get_current_user():
    """Retrieve current logged-in user from session or API token."""
    if hasattr(g, 'current_user') and g.current_user is not None:
        return g.current_user

    user_id = session.get('user_id')
    if user_id:
        user = UserModel.get_by_id(user_id)
        if user:
            g.current_user = user
            return user

    g.current_user = None
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
                return redirect(url_for('auth.login', next=request.url))
            
            # Admins have access to everything
            if user['role'] != 'admin' and user['role'] not in allowed_roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Forbidden', 'message': 'Access denied for this role'}), 403
                return jsonify({'error': 'Access Denied', 'message': f"Requires one of: {', '.join(allowed_roles)}"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
