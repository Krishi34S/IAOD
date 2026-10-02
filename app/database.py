import sqlite3
import os
from pathlib import Path
from flask import g, current_app
from werkzeug.security import generate_password_hash

SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'schema.sql'

def get_db():
    """Get the active database connection for the current Flask request context."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        # Enforce foreign key constraints in SQLite
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None):
    """Initialize the database tables and seed baseline reference data."""
    if app:
        with app.app_context():
            _execute_init()
    else:
        _execute_init()

def _execute_init():
    db = get_db()
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    db.executescript(schema_sql)
    db.commit()
    seed_initial_data(db)

def seed_initial_data(db):
    """Seed initial system users and reference catalog prices if empty."""
    cursor = db.cursor()
    
    # 1. Seed standard users for all 4 roles if not present
    default_users = [
        ('Admin User', 'admin@iaod.local', generate_password_hash('Admin@123'), 'admin'),
        ('Finance Officer', 'finance@iaod.local', generate_password_hash('Finance@123'), 'finance_staff'),
        ('Executive Management', 'management@iaod.local', generate_password_hash('Manage@123'), 'management'),
        ('Procurement User', 'user@iaod.local', generate_password_hash('User@123'), 'user')
    ]
    
    for name, email, pwd_hash, role in default_users:
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (name, email, pwd_hash, role)
            )

    # 2. Seed baseline benchmark reference prices for catalog items
    reference_items = [
        ('Dell Latitude 5420 Laptop', 'Electronics', 65000.0, 10.0, 'unit'),
        ('HP LaserJet Pro Printer M404n', 'Office Equipment', 22000.0, 12.0, 'unit'),
        ('Ergonomic Office Chair', 'Furniture', 8500.0, 15.0, 'unit'),
        ('A4 Copier Paper 75GSM (Box of 5)', 'Stationery', 1400.0, 8.0, 'box'),
        ('Cat6 Ethernet Cable (305m Drum)', 'Networking', 4500.0, 10.0, 'roll'),
        ('Cisco 24-Port Gigabit Switch', 'Networking', 28000.0, 10.0, 'unit'),
        ('Logitech Wireless Keyboard & Mouse Combo', 'Electronics', 1800.0, 15.0, 'set'),
        ('Samsung 27-inch 4K Monitor', 'Electronics', 24000.0, 10.0, 'unit'),
        ('Executive Conference Table (10-seater)', 'Furniture', 45000.0, 15.0, 'unit'),
        ('Whiteboard 6x4 ft Magnetic', 'Stationery', 3200.0, 10.0, 'unit'),
        ('Annual Cloud Server Maintenance', 'Services', 120000.0, 10.0, 'year'),
        ('IT Technical Support On-site', 'Services', 3500.0, 15.0, 'day')
    ]

    for item_name, category, price, tol, unit in reference_items:
        cursor.execute("SELECT reference_id FROM reference_prices WHERE item_name = ?", (item_name,))
        if not cursor.fetchone():
            cursor.execute(
                """INSERT INTO reference_prices 
                   (item_name, category, expected_unit_price, tolerance_percent, unit)
                   VALUES (?, ?, ?, ?, ?)""",
                (item_name, category, price, tol, unit)
            )

    db.commit()
