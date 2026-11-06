from app.api.invoices import invoices_api
from app.api.dashboard import dashboard_api
from app.api.reference_prices import ref_prices_api
from app.api.admin import admin_api
from app.api.reports import reports_api

__all__ = [
    'invoices_api',
    'dashboard_api',
    'ref_prices_api',
    'admin_api',
    'reports_api'
]
