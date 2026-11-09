import os
from flask import Flask
from app.config import Config
from app.database import close_db, init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Initialize DB schema if it doesn't exist yet
    with app.app_context():
        init_db(app)

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.views import views_bp
    from app.api.invoices import invoices_api
    from app.api.dashboard import dashboard_api
    from app.api.reference_prices import ref_prices_api
    from app.api.admin import admin_api
    from app.api.reports import reports_api

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(invoices_api)
    app.register_blueprint(dashboard_api)
    app.register_blueprint(ref_prices_api)
    app.register_blueprint(admin_api)
    app.register_blueprint(reports_api)

    return app
