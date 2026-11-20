import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.models import InvoiceModel, UserModel, ReferencePriceModel
from app.api.invoices import run_analysis_for_invoice

def seed_demo_database():
    app = create_app()
    with app.app_context():
        print("🌱 Seeding realistic invoice dataset for IAOD evaluation...")

        # 1. Fetch demo user (admin / procurement user)
        user = UserModel.get_by_email('user@iaod.local')
        if not user:
            user = UserModel.get_by_email('admin@iaod.local')
        user_id = user['user_id']

        # 2. Define realistic test invoices covering all SRS requirements
        demo_invoices = [
            # Case 1: Compliant, Clean Procurement Invoice (NORMAL)
            {
                'invoice_number': 'INV-2026-001',
                'vendor': 'Dell Technologies India',
                'invoice_date': '2026-03-10',
                'billed_subtotal': 130000.0,
                'tax_rate': 18.0,
                'tax_amount': 23400.0,
                'discount_amount': 0.0,
                'billed_total': 153400.0,
                'items': [
                    {
                        'description': 'Dell Latitude 5420 Laptop',
                        'category': 'Electronics',
                        'quantity': 2,
                        'unit_price': 65000.0,
                        'line_total': 130000.0
                    }
                ]
            },

            # Case 2: Overbilled Total Amount (FR-4)
            # Calculated: 25,500 + 18% tax (4,590) = 30,090. Billed: 36,000 (+5,910 excess)
            {
                'invoice_number': 'INV-2026-002',
                'vendor': 'Apex Workspace Solutions',
                'invoice_date': '2026-03-12',
                'billed_subtotal': 25500.0,
                'tax_rate': 18.0,
                'tax_amount': 4590.0,
                'discount_amount': 0.0,
                'billed_total': 36000.0,
                'items': [
                    {
                        'description': 'Ergonomic Office Chair',
                        'category': 'Furniture',
                        'quantity': 3,
                        'unit_price': 8500.0,
                        'line_total': 25500.0
                    }
                ]
            },

            # Case 3: Price Spike / Deviation against Reference Benchmark (FR-5.3, FR-5.4)
            # Benchmark for Cisco 24-Port Switch is 28,000 (tolerance 10%). Billed at 42,000 (+50% spike)
            {
                'invoice_number': 'INV-2026-003',
                'vendor': 'Matrix Networks & Telecom',
                'invoice_date': '2026-03-14',
                'billed_subtotal': 84000.0,
                'tax_rate': 18.0,
                'tax_amount': 15120.0,
                'discount_amount': 0.0,
                'billed_total': 99120.0,
                'items': [
                    {
                        'description': 'Cisco 24-Port Gigabit Switch',
                        'category': 'Networking',
                        'quantity': 2,
                        'unit_price': 42000.0,
                        'line_total': 84000.0
                    }
                ]
            },

            # Case 4: Line Item Arithmetic Calculation Error (FR-3.1, FR-3.4)
            # 5 * 1400 = 7,000. But line total billed as 9,500 (+2,500 error)
            {
                'invoice_number': 'INV-2026-004',
                'vendor': 'National Stationery Hub',
                'invoice_date': '2026-03-16',
                'billed_subtotal': 9500.0,
                'tax_rate': 18.0,
                'tax_amount': 1710.0,
                'discount_amount': 0.0,
                'billed_total': 11210.0,
                'items': [
                    {
                        'description': 'A4 Copier Paper 75GSM (Box of 5)',
                        'category': 'Stationery',
                        'quantity': 5,
                        'unit_price': 1400.0,
                        'line_total': 9500.0
                    }
                ]
            },

            # Case 5: Repeated / Duplicate Line Items in Same Invoice (FR-5.2)
            {
                'invoice_number': 'INV-2026-005',
                'vendor': 'Tezpur IT Peripherals',
                'invoice_date': '2026-03-18',
                'billed_subtotal': 3600.0,
                'tax_rate': 18.0,
                'tax_amount': 648.0,
                'discount_amount': 0.0,
                'billed_total': 4248.0,
                'items': [
                    {
                        'description': 'Logitech Wireless Keyboard & Mouse Combo',
                        'category': 'Electronics',
                        'quantity': 1,
                        'unit_price': 1800.0,
                        'line_total': 1800.0
                    },
                    {
                        'description': 'Logitech Wireless Keyboard & Mouse Combo',
                        'category': 'Electronics',
                        'quantity': 1,
                        'unit_price': 1800.0,
                        'line_total': 1800.0
                    }
                ]
            },

            # Case 6: Duplicate Invoice (FR-5.1) - Re-submitting invoice INV-2026-001
            {
                'invoice_number': 'INV-2026-001',
                'vendor': 'Dell Technologies India',
                'invoice_date': '2026-03-19',
                'billed_subtotal': 130000.0,
                'tax_rate': 18.0,
                'tax_amount': 23400.0,
                'discount_amount': 0.0,
                'billed_total': 153400.0,
                'items': [
                    {
                        'description': 'Dell Latitude 5420 Laptop',
                        'category': 'Electronics',
                        'quantity': 2,
                        'unit_price': 65000.0,
                        'line_total': 130000.0
                    }
                ]
            },

            # Case 7: Clean Services Invoice (NORMAL)
            {
                'invoice_number': 'INV-2026-007',
                'vendor': 'CloudSphere Infrastructure',
                'invoice_date': '2026-03-20',
                'billed_subtotal': 120000.0,
                'tax_rate': 18.0,
                'tax_amount': 21600.0,
                'discount_amount': 5000.0,
                'billed_total': 136600.0,
                'items': [
                    {
                        'description': 'Annual Cloud Server Maintenance',
                        'category': 'Services',
                        'quantity': 1,
                        'unit_price': 120000.0,
                        'line_total': 120000.0
                    }
                ]
            }
        ]

        created_count = 0
        for inv_data in demo_invoices:
            inv_id = InvoiceModel.create(inv_data, user_id=user_id)
            inv_data['invoice_id'] = inv_id
            
            # Map item_ids
            items = InvoiceModel.get_items(inv_id)
            for idx, item_row in enumerate(items):
                if idx < len(inv_data['items']):
                    inv_data['items'][idx]['item_id'] = item_row['item_id']

            # Run anomaly engine & persist
            res = run_analysis_for_invoice(inv_id, inv_data)
            created_count += 1
            print(f"  [{res['status']}] #{inv_data['invoice_number']} - {inv_data['vendor']} (Anomalies: {len(res['anomalies'])}, Score: {res['risk_score']:.0f})")

        print(f"\n✅ Successfully seeded and analyzed {created_count} realistic invoices!")

if __name__ == '__main__':
    seed_demo_database()
