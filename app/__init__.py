from flask import Flask
from .extensions import db


def create_app():
    app = Flask(__name__)

    # -------------------------------------------------
    # APP CONFIGURATION
    # -------------------------------------------------
    app.config["SECRET_KEY"] = "change-this-secret-key"

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # -------------------------------------------------
    # DATABASE
    # -------------------------------------------------
    db.init_app(app)

    # -------------------------------------------------
    # BLUEPRINTS
    # -------------------------------------------------

    # Main
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)

    # Authentication
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Investments
    try:
        from app.routes.investments import investments_bp
        app.register_blueprint(investments_bp)
    except ImportError:
        pass

    # Payments
    try:
        from app.routes.payments import payments_bp
        app.register_blueprint(payments_bp)
    except ImportError:
        pass

    # Admin
    try:
        from app.routes.admin import admin_bp
        app.register_blueprint(admin_bp)
    except ImportError:
        pass

    # Admin payment accounts
    try:
        from app.routes.admin_payments import admin_payments_bp
        app.register_blueprint(admin_payments_bp)
    except ImportError:
        pass

    # -------------------------------------------------
    # DATABASE TABLE CREATION
    # -------------------------------------------------
    with app.app_context():
        db.create_all()

    return app
