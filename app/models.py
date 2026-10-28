from datetime import datetime
from app.database import get_db

class UserModel:
    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        return db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    @staticmethod
    def get_by_email(email):
        db = get_db()
        return db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()

    @staticmethod
    def create(name, email, password_hash, role='user'):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash, role)
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def list_all():
        db = get_db()
        return db.execute("SELECT user_id, name, email, role, created_at FROM users ORDER BY created_at DESC").fetchall()

    @staticmethod
    def update_role(user_id, new_role):
        db = get_db()
        db.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
        db.commit()


class ReferencePriceModel:
    @staticmethod
    def list_all():
        db = get_db()
        return db.execute("SELECT * FROM reference_prices ORDER BY category, item_name").fetchall()

    @staticmethod
    def get_by_id(ref_id):
        db = get_db()
        return db.execute("SELECT * FROM reference_prices WHERE reference_id = ?", (ref_id,)).fetchone()

    @staticmethod
    def find_match(description, category=None):
        """Find the best reference price matching the description or category."""
        db = get_db()
        # 1. Exact match on item_name (case-insensitive)
        row = db.execute(
            "SELECT * FROM reference_prices WHERE LOWER(item_name) = LOWER(?)",
            (description.strip(),)
        ).fetchone()
        if row:
            return row

        # 2. Substring match
        row = db.execute(
            "SELECT * FROM reference_prices WHERE LOWER(?) LIKE '%' || LOWER(item_name) || '%' OR LOWER(item_name) LIKE '%' || LOWER(?) || '%'",
            (description.strip(), description.strip())
        ).fetchone()
        if row:
            return row

        # 3. Category match if category provided
        if category:
            row = db.execute(
                "SELECT * FROM reference_prices WHERE LOWER(category) = LOWER(?)",
                (category.strip(),)
            ).fetchone()
            if row:
                return row

        return None

    @staticmethod
    def create(item_name, category, expected_unit_price, tolerance_percent=15.0, unit='unit'):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO reference_prices (item_name, category, expected_unit_price, tolerance_percent, unit)
               VALUES (?, ?, ?, ?, ?)""",
            (item_name.strip(), category.strip(), expected_unit_price, tolerance_percent, unit.strip())
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update(ref_id, item_name, category, expected_unit_price, tolerance_percent, unit):
        db = get_db()
        db.execute(
            """UPDATE reference_prices 
               SET item_name = ?, category = ?, expected_unit_price = ?, tolerance_percent = ?, unit = ?, updated_at = CURRENT_TIMESTAMP
               WHERE reference_id = ?""",
            (item_name.strip(), category.strip(), expected_unit_price, tolerance_percent, unit.strip(), ref_id)
        )
        db.commit()

    @staticmethod
    def delete(ref_id):
        db = get_db()
        db.execute("DELETE FROM reference_prices WHERE reference_id = ?", (ref_id,))
        db.commit()


class InvoiceModel:
    @staticmethod
    def create(invoice_data, user_id):
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            """INSERT INTO invoices 
               (invoice_number, vendor, invoice_date, billed_subtotal, tax_rate, tax_amount, 
                discount_amount, billed_total, expected_subtotal, expected_tax, expected_total, 
                total_discrepancy, status, risk_score, user_id, raw_file_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                invoice_data['invoice_number'],
                invoice_data['vendor'],
                invoice_data['invoice_date'],
                invoice_data.get('billed_subtotal', 0.0),
                invoice_data.get('tax_rate', 0.0),
                invoice_data.get('tax_amount', 0.0),
                invoice_data.get('discount_amount', 0.0),
                invoice_data['billed_total'],
                invoice_data.get('expected_subtotal', 0.0),
                invoice_data.get('expected_tax', 0.0),
                invoice_data.get('expected_total', 0.0),
                invoice_data.get('total_discrepancy', 0.0),
                invoice_data.get('status', 'PENDING'),
                invoice_data.get('risk_score', 0.0),
                user_id,
                invoice_data.get('raw_file_name', None)
            )
        )
        invoice_id = cursor.lastrowid

        # Insert line items
        for item in invoice_data.get('items', []):
            cursor.execute(
                """INSERT INTO invoice_items 
                   (invoice_id, description, category, quantity, unit_price, line_total, expected_line_total)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    invoice_id,
                    item['description'],
                    item.get('category', 'General'),
                    item['quantity'],
                    item['unit_price'],
                    item['line_total'],
                    item.get('expected_line_total', round(item['quantity'] * item['unit_price'], 2))
                )
            )

        db.commit()
        return invoice_id

    @staticmethod
    def get_by_id(invoice_id):
        db = get_db()
        invoice = db.execute(
            """SELECT i.*, u.name as submitter_name, u.role as submitter_role 
               FROM invoices i 
               JOIN users u ON i.user_id = u.user_id 
               WHERE i.invoice_id = ?""",
            (invoice_id,)
        ).fetchone()
        return invoice

    @staticmethod
    def get_items(invoice_id):
        db = get_db()
        return db.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,)).fetchall()

    @staticmethod
    def get_anomalies(invoice_id):
        db = get_db()
        return db.execute(
            """SELECT a.*, item.description as item_description 
               FROM anomalies a 
               LEFT JOIN invoice_items item ON a.item_id = item.item_id 
               WHERE a.invoice_id = ? 
               ORDER BY 
                 CASE a.severity 
                   WHEN 'CRITICAL' THEN 1 
                   WHEN 'HIGH' THEN 2 
                   WHEN 'MEDIUM' THEN 3 
                   ELSE 4 
                 END, a.anomaly_id ASC""",
            (invoice_id,)
        ).fetchall()

    @staticmethod
    def update_analysis_results(invoice_id, calc_results, anomalies, risk_score, status):
        db = get_db()
        cursor = db.cursor()

        # Update invoice totals and status
        cursor.execute(
            """UPDATE invoices 
               SET expected_subtotal = ?, expected_tax = ?, expected_total = ?, 
                   total_discrepancy = ?, status = ?, risk_score = ?
               WHERE invoice_id = ?""",
            (
                calc_results['expected_subtotal'],
                calc_results['expected_tax'],
                calc_results['expected_total'],
                calc_results['total_discrepancy'],
                status,
                risk_score,
                invoice_id
            )
        )

        # Clear any prior anomalies for this invoice to prevent duplication on re-analysis
        cursor.execute("DELETE FROM anomalies WHERE invoice_id = ?", (invoice_id,))

        # Insert new anomalies
        for a in anomalies:
            cursor.execute(
                """INSERT INTO anomalies 
                   (invoice_id, item_id, anomaly_type, severity, expected_value, affected_value, difference, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    invoice_id,
                    a.get('item_id'),
                    a['anomaly_type'],
                    a['severity'],
                    a.get('expected_value'),
                    a.get('affected_value'),
                    a.get('difference'),
                    a['explanation']
                )
            )

        db.commit()

    @staticmethod
    def list_all(query=None, status=None, vendor=None, limit=100):
        db = get_db()
        sql = """SELECT i.*, u.name as submitter_name, 
                 (SELECT COUNT(*) FROM anomalies WHERE invoice_id = i.invoice_id) as anomaly_count 
                 FROM invoices i 
                 JOIN users u ON i.user_id = u.user_id 
                 WHERE 1=1"""
        params = []

        if query:
            sql += " AND (i.invoice_number LIKE ? OR i.vendor LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        if status:
            sql += " AND i.status = ?"
            params.append(status)
        if vendor:
            sql += " AND i.vendor LIKE ?"
            params.append(f"%{vendor}%")

        sql += " ORDER BY i.created_at DESC LIMIT ?"
        params.append(limit)

        return db.execute(sql, params).fetchall()

    @staticmethod
    def find_potential_duplicates(vendor, invoice_number, current_invoice_id=None):
        db = get_db()
        sql = """SELECT * FROM invoices 
                 WHERE LOWER(vendor) = LOWER(?) AND LOWER(invoice_number) = LOWER(?)"""
        params = [vendor.strip(), invoice_number.strip()]
        if current_invoice_id:
            sql += " AND invoice_id != ?"
            params.append(current_invoice_id)
        return db.execute(sql, params).fetchall()

    @staticmethod
    def find_historical_item_prices(description, exclude_invoice_id=None):
        db = get_db()
        sql = """SELECT item.unit_price, item.quantity, inv.invoice_date, inv.vendor 
                 FROM invoice_items item
                 JOIN invoices inv ON item.invoice_id = inv.invoice_id
                 WHERE LOWER(item.description) = LOWER(?)"""
        params = [description.strip()]
        if exclude_invoice_id:
            sql += " AND inv.invoice_id != ?"
            params.append(exclude_invoice_id)
        sql += " ORDER BY inv.invoice_date DESC LIMIT 20"
        return db.execute(sql, params).fetchall()

    @staticmethod
    def get_dashboard_statistics():
        db = get_db()
        stats = {}
        
        # Total counts
        stats['total_invoices'] = db.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        stats['normal_invoices'] = db.execute("SELECT COUNT(*) FROM invoices WHERE status = 'NORMAL'").fetchone()[0]
        stats['suspicious_invoices'] = db.execute("SELECT COUNT(*) FROM invoices WHERE status = 'SUSPICIOUS'").fetchone()[0]
        stats['pending_invoices'] = db.execute("SELECT COUNT(*) FROM invoices WHERE status = 'PENDING'").fetchone()[0]

        # Financial totals
        financials = db.execute("""
            SELECT 
                COALESCE(SUM(billed_total), 0) as total_billed,
                COALESCE(SUM(expected_total), 0) as total_expected,
                COALESCE(SUM(CASE WHEN total_discrepancy > 0 THEN total_discrepancy ELSE 0 END), 0) as total_overbilled
            FROM invoices
        """).fetchone()
        stats['total_billed'] = financials['total_billed']
        stats['total_expected'] = financials['total_expected']
        stats['total_overbilled'] = financials['total_overbilled']

        # Anomaly type breakdown
        breakdown = db.execute("""
            SELECT anomaly_type, COUNT(*) as count 
            FROM anomalies 
            GROUP BY anomaly_type 
            ORDER BY count DESC
        """).fetchall()
        stats['anomaly_breakdown'] = [dict(b) for b in breakdown]

        # Severity breakdown
        sev = db.execute("""
            SELECT severity, COUNT(*) as count 
            FROM anomalies 
            GROUP BY severity 
            ORDER BY 
              CASE severity 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                ELSE 4 
              END
        """).fetchall()
        stats['severity_breakdown'] = [dict(s) for s in sev]

        # Recent 5 invoices
        recent = db.execute("""
            SELECT i.*, 
                   (SELECT COUNT(*) FROM anomalies WHERE invoice_id = i.invoice_id) as anomaly_count 
            FROM invoices i 
            ORDER BY i.created_at DESC LIMIT 5
        """).fetchall()
        stats['recent_invoices'] = [dict(r) for r in recent]

        return stats
