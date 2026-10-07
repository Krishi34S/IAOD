from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import UserModel
from app.auth.utils import get_current_user, login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'user').strip().lower()

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400

    if role not in ('user', 'finance_staff', 'management', 'admin'):
        role = 'user'

    existing = UserModel.get_by_email(email)
    if existing:
        return jsonify({'error': 'An account with this email already exists'}), 409

    pwd_hash = generate_password_hash(password)
    user_id = UserModel.create(name, email, pwd_hash, role)
    
    session['user_id'] = user_id
    user = UserModel.get_by_id(user_id)

    return jsonify({
        'message': 'Registration successful',
        'user': {
            'user_id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        }
    }), 201

@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = UserModel.get_by_email(email)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    session['user_id'] = user['user_id']

    return jsonify({
        'message': 'Login successful',
        'user': {
            'user_id': user['user_id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        }
    }), 200

@auth_bp.route('/api/auth/logout', methods=['POST', 'GET'])
def api_logout():
    session.clear()
    if request.is_json:
        return jsonify({'message': 'Logged out successfully'}), 200
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def api_me():
    user = get_current_user()
    return jsonify({
        'user_id': user['user_id'],
        'name': user['name'],
        'email': user['email'],
        'role': user['role']
    })

# Web Routes for browser UI
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = UserModel.get_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            next_url = request.args.get('next') or url_for('dashboard_views.index')
            return redirect(next_url)
        flash('Invalid email or password', 'error')
    return render_template('login.html', user=get_current_user())

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'user').strip()

        if role not in ('user', 'finance_staff', 'management', 'admin'):
            role = 'user'

        if UserModel.get_by_email(email):
            flash('An account with this email already exists', 'error')
        else:
            pwd_hash = generate_password_hash(password)
            user_id = UserModel.create(name, email, pwd_hash, role)
            session['user_id'] = user_id
            return redirect(url_for('dashboard_views.index'))

    return render_template('register.html', user=get_current_user())

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
