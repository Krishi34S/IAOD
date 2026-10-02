-- Invoice Anomaly & Overbilling Detector (IAOD)
-- Relational Database Schema
-- Compatible with SQLite and MySQL / MariaDB

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'user', -- 'admin', 'finance_staff', 'management', 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Reference Prices Table
CREATE TABLE IF NOT EXISTS reference_prices (
    reference_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL,
    expected_unit_price REAL NOT NULL,
    tolerance_percent REAL NOT NULL DEFAULT 15.0,
    unit VARCHAR(50) DEFAULT 'unit',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number VARCHAR(100) NOT NULL,
    vendor VARCHAR(150) NOT NULL,
    invoice_date DATE NOT NULL,
    billed_subtotal REAL NOT NULL DEFAULT 0.0,
    tax_rate REAL NOT NULL DEFAULT 0.0,
    tax_amount REAL NOT NULL DEFAULT 0.0,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    billed_total REAL NOT NULL,
    expected_subtotal REAL DEFAULT 0.0,
    expected_tax REAL DEFAULT 0.0,
    expected_total REAL DEFAULT 0.0,
    total_discrepancy REAL DEFAULT 0.0,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'NORMAL', 'SUSPICIOUS'
    risk_score REAL DEFAULT 0.0, -- 0 to 100
    user_id INTEGER NOT NULL,
    raw_file_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 4. Invoice Items Table
CREATE TABLE IF NOT EXISTS invoice_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    description VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    expected_line_total REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE
);

-- 5. Anomalies Table
CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    item_id INTEGER,
    anomaly_type VARCHAR(50) NOT NULL, -- CALCULATION_ERROR, OVERBILLING, DUPLICATE_INVOICE, DUPLICATE_ITEM, PRICE_ANOMALY, TAX_MISMATCH, DISCOUNT_MISMATCH
    severity VARCHAR(20) NOT NULL,     -- LOW, MEDIUM, HIGH, CRITICAL
    affected_value REAL,
    expected_value REAL,
    difference REAL,
    explanation TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES invoice_items(item_id) ON DELETE SET NULL
);

-- 6. Analysis Reports Table
CREATE TABLE IF NOT EXISTS analysis_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    total_anomalies INTEGER DEFAULT 0,
    risk_level VARCHAR(20) DEFAULT 'LOW',
    summary TEXT,
    report_file VARCHAR(255),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoices_vendor_num ON invoices(vendor, invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_anomalies_invoice ON anomalies(invoice_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);
