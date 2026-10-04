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

