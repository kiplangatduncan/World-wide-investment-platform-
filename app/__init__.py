from flask import Flask
from .extensions import db


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = "change-this-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize database
    db.init_app(app)

    # Import blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.investments import investments_bp
    from app.routes.payments import payments_bp
    from app.routes.admin import admin_bp
    from app.routes.admin_payments import admin_payments_bp

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(investments_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_payments_bp)

    # M-Pesa blueprint
    try:
        from app.mpesa.mpesa import mpesa_bp
        app.register_blueprint(mpesa_bp)
    except ImportError:
        pass

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
