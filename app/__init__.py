from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

from config import Config


# ============================================================
# EXTENSIONS
# ============================================================

db = SQLAlchemy()

login_manager = LoginManager()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."


# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app():

    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Initialize login system
    login_manager.init_app(app)

    # ========================================================
    # REGISTER BLUEPRINTS
    # ========================================================

    # Authentication
    try:
        from app.auth.routes import auth_bp
        app.register_blueprint(auth_bp)
    except ImportError:
        pass

    # Investments
    try:
        from app.investments.routes import investments_bp
        app.register_blueprint(investments_bp)
    except ImportError:
        pass
    # Main application routes
    try:
        from app.routes.main import main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass
    # Payments
    try:
        from app.routes.payments import payments_bp
        app.register_blueprint(payments_bp)
    except ImportError:
        pass

    # Payment callbacks
    try:
        from app.payments.callbacks import callbacks_bp
        app.register_blueprint(callbacks_bp)
    except ImportError:
        pass

    # Admin
    try:
        from app.admin.routes import admin_bp
        app.register_blueprint(admin_bp)
    except ImportError:
        pass

    # Admin payment accounts
    try:
        from app.routes.admin_payments import admin_payments_bp
        app.register_blueprint(admin_payments_bp)
    except ImportError:
        pass

    # ========================================================
    # CREATE DATABASE TABLES
    # ========================================================

    with app.app_context():
        from app import models

        db.create_all()

    return app


# ============================================================
# FLASK-LOGIN USER LOADER
# ============================================================

@login_manager.user_loader
def load_user(user_id):

    from app.models import User

    try:
        return db.session.get(
            User,
            int(user_id)
        )

    except (ValueError, TypeError):
        return None
