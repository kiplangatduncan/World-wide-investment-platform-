import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import phonenumbers
import pycountry

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "CHANGE-ME-IN-PRODUCTION"
)

database_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///investment_platform.db"
)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================================================
# CONFIGURATION
# =========================================================

PLATFORM_NAME = "GlobalVest"

# This is deliberately configurable.
# It should NOT be advertised as a guaranteed investment return.
DEFAULT_DAILY_GROWTH_RATE = 2.0

MATURITY_DAYS = 4


# =========================================================
# DATABASE MODELS
# =========================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )

    full_name = db.Column(db.String(120), nullable=False)

    email = db.Column(
        db.String(160),
        unique=True,
        nullable=False,
        index=True
    )

    phone = db.Column(db.String(40), nullable=False)

    country = db.Column(db.String(100), nullable=False)

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="USD"
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    balance = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    is_admin = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    investments = db.relationship(
        "Investment",
        backref="user",
        lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    reference = db.Column(
        db.String(40),
        unique=True,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    daily_rate = db.Column(
        db.Float,
        nullable=False
    )

    maturity_days = db.Column(
        db.Integer,
        nullable=False,
        default=MATURITY_DAYS
    )

    start_date = db.Column(
        db.DateTime,
        nullable=False
    )

    maturity_date = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="active"
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    @property
    def days_elapsed(self):
        now = datetime.now(timezone.utc)

        elapsed = (now - self.start_date).total_seconds() / 86400

        return max(
            0,
            min(self.maturity_days, elapsed)
        )

    @property
    def current_value(self):
        growth = (
            self.amount
            * (self.daily_rate / 100)
            * self.days_elapsed
        )

        return self.amount + growth

    @property
    def projected_value(self):
        growth = (
            self.amount
            * (self.daily_rate / 100)
            * self.maturity_days
        )

        return self.amount + growth


class PlatformSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    daily_rate = db.Column(
        db.Float,
        nullable=False,
        default=DEFAULT_DAILY_GROWTH_RATE
    )

    maturity_days = db.Column(
        db.Integer,
        nullable=False,
        default=MATURITY_DAYS
    )


# =========================================================
# COUNTRY / CURRENCY DATA
# =========================================================

def get_countries():
    countries = []

    for country in pycountry.countries:
        countries.append({
            "code": country.alpha_2,
            "name": country.name
        })

    return sorted(
        countries,
        key=lambda x: x["name"]
    )


def get_currency_codes():
    currencies = set()

    for currency in pycountry.currencies:
        currencies.add(currency.alpha_4217)

    return sorted(currencies)


COUNTRIES = get_countries()
CURRENCIES = get_currency_codes()


# =========================================================
# HELPERS
# =========================================================

def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("user_id"):
            flash(
                "Please log in to continue.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        user = current_user()

        if not user or not user.is_admin:
            flash(
                "Administrator access required.",
                "danger"
            )

            return redirect(
                url_for("dashboard")
            )

        return view(*args, **kwargs)

    return wrapped


def get_platform_settings():

    settings = PlatformSetting.query.first()

    if not settings:

        settings = PlatformSetting(
            daily_rate=DEFAULT_DAILY_GROWTH_RATE,
            maturity_days=MATURITY_DAYS
        )

        db.session.add(settings)
        db.session.commit()

    return settings


def valid_phone(phone, country_code):

    try:

        parsed = phonenumbers.parse(
            phone,
            country_code
        )

        return phonenumbers.is_valid_number(parsed)

    except Exception:

        return False


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

    user = current_user()

    return render_template(
        "index.html",
        user=user,
        platform_name=PLATFORM_NAME
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        country = request.form.get(
            "country",
            ""
        ).strip()

        currency = request.form.get(
            "currency",
            ""
        ).strip().upper()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not all([
            full_name,
            email,
            phone,
            country,
            currency,
            password
        ]):

            flash(
                "Please complete all fields.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "An account with that email already exists.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        country_obj = next(
            (
                item for item in COUNTRIES
                if item["name"] == country
            ),
            None
        )

        if not country_obj:

            flash(
                "Please select a valid country.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if currency not in CURRENCIES:

            flash(
                "Please select a valid currency.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if not valid_phone(
            phone,
            country_obj["code"]
        ):

            flash(
                "Please enter a valid phone number.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            country=country,
            currency=currency
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html",
        countries=COUNTRIES,
        currencies=CURRENCIES,
        platform_name=PLATFORM_NAME
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            email=email
        ).first()

        if not user or not user.check_password(password):

            flash(
                "Invalid email or password.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        session.clear()

        session["user_id"] = user.id

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "login.html",
        platform_name=PLATFORM_NAME
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = current_user()

    investments = Investment.query.filter_by(
        user_id=user.id
    ).order_by(
        Investment.created_at.desc()
    ).all()

    active_investments = [
        investment
        for investment in investments
        if investment.status == "active"
    ]

    total_invested = sum(
        investment.amount
        for investment in investments
    )

    current_value = sum(
        investment.current_value
        for investment in active_investments
    )

    return render_template(
        "dashboard.html",
        user=user,
        investments=investments,
        active_investments=active_investments,
        total_invested=total_invested,
        current_value=current_value,
        platform_name=PLATFORM_NAME
    )


# =========================================================
# CREATE INVESTMENT
# =========================================================

@app.route("/invest", methods=["GET", "POST"])
@login_required
def invest():

    user = current_user()
    settings = get_platform_settings()

    if request.method == "POST":

        amount_text = request.form.get(
            "amount",
            ""
        ).strip()

        try:

            amount = float(amount_text)

        except ValueError:

            flash(
                "Enter a valid investment amount.",
                "danger"
            )

            return redirect(
                url_for("invest")
            )

        if amount <= 0:

            flash(
                "Investment amount must be greater than zero.",
                "danger"
            )

            return redirect(
                url_for("invest")
            )

        if amount > user.balance:

            flash(
                "Insufficient available balance.",
                "danger"
            )

            return redirect(
                url_for("invest")
            )

        now = datetime.now(timezone.utc)

        investment = Investment(
            reference="INV-" + uuid.uuid4().hex[:12].upper(),
            user_id=user.id,
            amount=amount,
            daily_rate=settings.daily_rate,
            maturity_days=settings.maturity_days,
            start_date=now,
            maturity_date=now + timedelta(
                days=settings.maturity_days
            ),
            status="active"
        )

        user.balance -= amount

        db.session.add(investment)

        db.session.commit()

        flash(
            "Investment created successfully.",
            "success"
        )

        return redirect(
            url_for("investments")
        )

    return render_template(
        "invest.html",
        user=user,
        settings=settings,
        platform_name=PLATFORM_NAME
    )


# =========================================================
# INVESTMENTS
# =========================================================

@app.route("/investments")
@login_required
def investments():

    user = current_user()

    investment_list = Investment.query.filter_by(
        user_id=user.id
    ).order_by(
        Investment.created_at.desc()
    ).all()

    return render_template(
        "investments.html",
        user=user,
        investments=investment_list,
        platform_name=PLATFORM_NAME
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
@login_required
def profile():

    user = current_user()

    return render_template(
        "profile.html",
        user=user,
        platform_name=PLATFORM_NAME
    )


# =========================================================
# ADMIN
# =========================================================

@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():

    settings = get_platform_settings()

    if request.method == "POST":

        try:

            daily_rate = float(
                request.form.get(
                    "daily_rate",
                    settings.daily_rate
                )
            )

            maturity_days = int(
                request.form.get(
                    "maturity_days",
                    settings.maturity_days
                )
            )

            if daily_rate < 0:

                raise ValueError()

            if maturity_days < 1:

                raise ValueError()

            settings.daily_rate = daily_rate
            settings.maturity_days = maturity_days

            db.session.commit()

            flash(
                "Platform settings updated.",
                "success"
            )

        except ValueError:

            flash(
                "Please enter valid settings.",
                "danger"
            )

        return redirect(
            url_for("admin")
        )

    users_count = User.query.count()

    investments_count = Investment.query.count()

    total_invested = db.session.query(
        db.func.sum(Investment.amount)
    ).scalar() or 0

    return render_template(
        "admin.html",
        settings=settings,
        users_count=users_count,
        investments_count=investments_count,
        total_invested=total_invested,
        platform_name=PLATFORM_NAME
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

with app.app_context():

    db.create_all()

    settings = PlatformSetting.query.first()

    if not settings:

        settings = PlatformSetting(
            daily_rate=DEFAULT_DAILY_GROWTH_RATE,
            maturity_days=MATURITY_DAYS
        )

        db.session.add(settings)

    admin_email = os.getenv(
        "ADMIN_EMAIL"
    )

    admin_password = os.getenv(
        "ADMIN_PASSWORD"
    )

    if admin_email and admin_password:

        admin = User.query.filter_by(
            email=admin_email.lower()
        ).first()

        if not admin:

            admin = User(
                full_name="Platform Administrator",
                email=admin_email.lower(),
                phone="",
                country="",
                currency="USD",
                is_admin=True
            )

            admin.set_password(admin_password)

            db.session.add(admin)

    db.session.commit()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
      )
