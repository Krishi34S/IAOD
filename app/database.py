import sqlite3
from pathlib import Path
from flask import g, current_app
from werkzeug.security import generate_password_hash

SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'schema.sql'

def get_db():
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    if app:
        with app.app_context():
            _execute_init()
    else:
        _execute_init()

def _execute_init():
    db = get_db()
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    db.commit()
    seed_initial_data(db)

def seed_initial_data(db):
    cursor = db.cursor()
    default_users = [
        ('Admin User', 'admin@iaod.local', generate_password_hash('Admin@123'), 'admin'),
        ('Finance Officer', 'finance@iaod.local', generate_password_hash('Finance@123'), 'finance_staff'),
        ('Procurement User', 'user@iaod.local', generate_password_hash('User@123'), 'user')
    ]
    for name, email, pwd_hash, role in default_users:
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, pwd_hash, role)
            )
    db.commit()
