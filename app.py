import os
import uuid
import base64
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from functools import wraps

import requests
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
    jsonify,
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# GLOBALVEST CONFIGURATION
# ============================================================

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

# Render sometimes provides postgres://
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ============================================================
# PLATFORM SETTINGS
# ============================================================

PLATFORM_NAME = "GlobalVest"

# This is a platform setting, NOT a guaranteed return.
DEFAULT_DAILY_GROWTH_RATE = Decimal("2.0")

MATURITY_DAYS = 4


# ============================================================
# BASIC HELPERS
# ============================================================

def utc_now():
    """Return current UTC time as a simple datetime."""
    return datetime.utcnow()


def money(value):
    """Safely convert a value to Decimal money."""
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def generate_public_id():
    return str(uuid.uuid4())


# ============================================================
# USER MODEL
# ============================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=generate_public_id
    )

    full_name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(160),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(30),
        nullable=True
    )

    country = db.Column(
        db.String(80),
        nullable=True
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="KES"
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    balance = db.Column(
        db.Numeric(18, 2),
        nullable=False,
        default=0
    )

    is_admin = db.Column(
        db.Boolean,
        default=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=utc_now
    )


# ============================================================
# DEPOSIT MODEL
# ============================================================

class Deposit(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    reference = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        default=lambda: "DEP-" + uuid.uuid4().hex[:12].upper()
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    method = db.Column(
        db.String(50),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="pending"
    )

    mpesa_receipt = db.Column(
        db.String(100),
        nullable=True
    )

    checkout_request_id = db.Column(
        db.String(100),
        nullable=True,
        unique=True
    )

    created_at = db.Column(
        db.DateTime,
        default=utc_now
    )

    user = db.relationship(
        "User",
        backref="deposits"
    )


# ============================================================
# INVESTMENT MODEL
# ============================================================

class Investment(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    reference = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        default=lambda: "INV-" + uuid.uuid4().hex[:12].upper()
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    daily_rate = db.Column(
        db.Numeric(8, 4),
        nullable=False
    )

    start_date = db.Column(
        db.DateTime,
        default=utc_now
    )

    maturity_date = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="active"
    )

    created_at = db.Column(
        db.DateTime,
        default=utc_now
    )

    user = db.relationship(
        "User",
        backref="investments"
    )


# ============================================================
# WITHDRAWAL MODEL
# ============================================================

class Withdrawal(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    reference = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        default=lambda: "WDR-" + uuid.uuid4().hex[:12].upper()
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    method = db.Column(
        db.String(50),
        nullable=False
    )

    account = db.Column(
        db.String(160),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=utc_now
    )

    user = db.relationship(
        "User",
        backref="withdrawals"
    )


# ============================================================
# TRANSACTION MODEL
# ============================================================

class Transaction(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    reference = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        default=lambda: "TX-" + uuid.uuid4().hex[:12].upper()
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    transaction_type = db.Column(
        db.String(50),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=utc_now
    )

    user = db.relationship(
        "User",
        backref="transactions"
    )


# ============================================================
# PAYMENT ACCOUNT MODEL
# ============================================================

class PaymentAccount(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    country = db.Column(
        db.String(80),
        nullable=False
    )

    method = db.Column(
        db.String(80),
        nullable=False
    )

    account_name = db.Column(
        db.String(160),
        nullable=False
    )

    account_number = db.Column(
        db.String(160),
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=utc_now
    )


# ============================================================
# PLATFORM SETTINGS MODEL
# ============================================================

class PlatformSetting(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    key = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    value = db.Column(
        db.String(255),
        nullable=True
    )


# ============================================================
# END OF PART 1
# ============================================================
# ============================================================
# PART 2 — HELPERS, AUTHENTICATION & M-PESA
# ============================================================

def get_setting(key, default=None):
    setting = PlatformSetting.query.filter_by(key=key).first()

    if setting:
        return setting.value

    return default


def set_setting(key, value):
    setting = PlatformSetting.query.filter_by(key=key).first()

    if not setting:
        setting = PlatformSetting(key=key)
        db.session.add(setting)

    setting.value = str(value)
    db.session.commit()

    return setting


def get_daily_rate():
    value = get_setting(
        "daily_growth_rate",
        str(DEFAULT_DAILY_GROWTH_RATE)
    )

    return money(value)


def investment_profit(investment):
    """
    Calculate simple daily growth based on elapsed days.

    This is a calculation for the platform's configured rate.
    It is NOT a guarantee of investment returns.
    """

    if investment.status != "active":
        return Decimal("0.00")

    today = utc_now()

    if today <= investment.start_date:
        return Decimal("0.00")

    end_date = min(today, investment.maturity_date)

    elapsed_seconds = (
        end_date - investment.start_date
    ).total_seconds()

    days = int(elapsed_seconds // 86400)

    if days <= 0:
        return Decimal("0.00")

    rate = money(investment.daily_rate)

    profit = (
        money(investment.amount)
        * rate
        * Decimal(days)
        / Decimal("100")
    )

    return money(profit)


def investment_total_value(investment):
    return money(
        investment.amount
        + investment_profit(investment)
    )


def create_transaction(
    user,
    transaction_type,
    amount,
    description=""
):
    transaction = Transaction(
        user_id=user.id,
        transaction_type=transaction_type,
        amount=money(amount),
        description=description
    )

    db.session.add(transaction)

    return transaction


@login_required
@login_required
def invest():
    user = current_user()

    if request.method == "POST":
        amount = money(
            request.form.get("amount", "0")
        )

        if amount <= Decimal("0.00"):
            flash(
                "Enter a valid investment amount.",
                "danger"
            )
            return render_template(
                "invest.html",
                user=user
            )

        if money(user.balance) < amount:
            flash(
                "Insufficient wallet balance.",
                "danger"
            )
            return render_template(
                "invest.html",
                user=user
            )

        rate = get_daily_rate()
        start_date = utc_now()

        maturity_date = (
            start_date
            + timedelta(days=MATURITY_DAYS)
        )

        investment = Investment(
            user_id=user.id,
            amount=amount,
            daily_rate=rate,
            start_date=start_date,
            maturity_date=maturity_date,
            status="active"
        )

        user.balance = (
            money(user.balance) - amount
        )

        db.session.add(investment)

        create_transaction(
            user,
            "investment",
            -amount,
            "Investment created"
        )

        db.session.commit()

        flash(
            "Your investment has been created successfully.",
            "success"
        )

        return redirect(
            url_for("investments")
        )

    return render_template(
        "invest.html",
        user=user
    )

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        user_id = session.get("user_id")

        if not user_id:
            return redirect(url_for("login"))

        user = db.session.get(User, user_id)

        if not user or not user.is_admin:
            flash(
                "Administrator access required.",
                "danger"
            )

            return redirect(url_for("dashboard"))

        return view(*args, **kwargs)

    return wrapped


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


# ============================================================
# COUNTRY & CURRENCY HELPERS
# ============================================================

SUPPORTED_CURRENCIES = [
    ("KES", "Kenyan Shilling"),
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("GBP", "British Pound"),
    ("NGN", "Nigerian Naira"),
    ("GHS", "Ghanaian Cedi"),
    ("TZS", "Tanzanian Shilling"),
    ("UGX", "Ugandan Shilling"),
    ("ZAR", "South African Rand"),
    ("AED", "UAE Dirham"),
    ("INR", "Indian Rupee"),
    ("CAD", "Canadian Dollar"),
    ("AUD", "Australian Dollar"),
]


def get_countries():
    countries = []

    for country in pycountry.countries:
        name = getattr(country, "name", None)

        if name:
            countries.append(name)

    return sorted(set(countries))


def get_currencies():
    return SUPPORTED_CURRENCIES


# ============================================================
# PHONE NUMBER HELPERS
# ============================================================

def normalize_phone(phone, country="KE"):
    if not phone:
        return None

    phone = str(phone).strip()

    try:
        parsed = phonenumbers.parse(
            phone,
            country
        )

        if not phonenumbers.is_valid_number(parsed):
            return None

        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )

    except Exception:
        return None


def mpesa_phone(phone):
    """
    Convert a Kenyan phone number into the format
    normally expected by the Daraja API.
    """

    normalized = normalize_phone(phone, "KE")

    if not normalized:
        return None

    number = normalized.replace("+", "")

    if number.startswith("254"):
        return number

    return None


# ============================================================
# M-PESA CONFIGURATION
# ============================================================

MPESA_ENVIRONMENT = os.getenv(
    "MPESA_ENVIRONMENT",
    "sandbox"
).lower()

MPESA_CONSUMER_KEY = os.getenv(
    "MPESA_CONSUMER_KEY",
    ""
)

MPESA_CONSUMER_SECRET = os.getenv(
    "MPESA_CONSUMER_SECRET",
    ""
)

MPESA_SHORTCODE = os.getenv(
    "MPESA_SHORTCODE",
    ""
)

MPESA_PASSKEY = os.getenv(
    "MPESA_PASSKEY",
    ""
)

MPESA_CALLBACK_URL = os.getenv(
    "MPESA_CALLBACK_URL",
    ""
)


def mpesa_base_url():
    if MPESA_ENVIRONMENT == "production":
        return "https://api.safaricom.co.ke"

    return "https://sandbox.safaricom.co.ke"


def mpesa_access_token():
    """
    Request an OAuth access token from Safaricom Daraja.
    """

    if not MPESA_CONSUMER_KEY:
        return None

    if not MPESA_CONSUMER_SECRET:
        return None

    credentials = (
        MPESA_CONSUMER_KEY
        + ":"
        + MPESA_CONSUMER_SECRET
    )

    encoded = base64.b64encode(
        credentials.encode("utf-8")
    ).decode("utf-8")

    headers = {
        "Authorization": "Basic " + encoded
    }

    url = (
        mpesa_base_url()
        + "/oauth/v1/generate?grant_type=client_credentials"
    )

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        return data.get("access_token")

    except Exception:
        return None


def mpesa_password(timestamp):
    """
    Daraja password:

    Base64(
        BusinessShortCode
        + Passkey
        + Timestamp
    )
    """

    raw = (
        MPESA_SHORTCODE
        + MPESA_PASSKEY
        + timestamp
    )

    return base64.b64encode(
        raw.encode("utf-8")
    ).decode("utf-8")


def initiate_mpesa_stk(
    phone,
    amount,
    account_reference,
    description
):
    """
    Initiate an M-Pesa STK Push.

    IMPORTANT:
    A successful API response only means Safaricom
    accepted the request. The wallet must NOT be credited
    until the callback reports ResultCode == 0.
    """

    token = mpesa_access_token()

    if not token:
        return {
            "success": False,
            "message": "M-Pesa credentials are not configured."
        }

    phone_number = mpesa_phone(phone)

    if not phone_number:
        return {
            "success": False,
            "message": "Enter a valid Kenyan M-Pesa number."
        }

    if not MPESA_SHORTCODE:
        return {
            "success": False,
            "message": "M-Pesa shortcode is not configured."
        }

    if not MPESA_PASSKEY:
        return {
            "success": False,
            "message": "M-Pesa passkey is not configured."
        }

    if not MPESA_CALLBACK_URL:
        return {
            "success": False,
            "message": "M-Pesa callback URL is not configured."
        }

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d%H%M%S"
    )

    password = mpesa_password(timestamp)

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(money(amount)),
        "PartyA": phone_number,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": description[:50],
    }

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }

    url = (
        mpesa_base_url()
        + "/mpesa/stkpush/v1/processrequest"
    )

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )

        data = response.json()

        if response.ok and data.get("ResponseCode") == "0":
            return {
                "success": True,
                "data": data
            }

        return {
            "success": False,
            "message": data.get(
                "errorMessage",
                data.get(
                    "ResponseDescription",
                    "M-Pesa request was not accepted."
                )
            ),
            "data": data
        }

    except Exception as exc:
        return {
            "success": False,
            "message": "Unable to connect to M-Pesa.",
            "error": str(exc)
        }


# ============================================================
# END OF PART 2
# ============================================================
# ============================================================
# PART 3 — PUBLIC & USER ROUTES
# ============================================================


@app.context_processor
def inject_globalvest_data():
    user = current_user()

    return {
        "platform_name": PLATFORM_NAME,
        "current_user": user,
        "daily_rate": get_daily_rate(),
        "countries": get_countries(),
        "currencies": get_currencies(),
    }


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# REGISTER
# ============================================================

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
            "KES"
        ).strip().upper()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Basic validation
        if not full_name:
            flash(
                "Please enter your full name.",
                "danger"
            )
            return render_template("register.html")

        if not email:
            flash(
                "Please enter your email.",
                "danger"
            )
            return render_template("register.html")

        if not password:
            flash(
                "Please create a password.",
                "danger"
            )
            return render_template("register.html")

        if len(password) < 6:
            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )
            return render_template("register.html")

        if password != confirm_password:
            flash(
                "Passwords do not match.",
                "danger"
            )
            return render_template("register.html")

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash(
                "An account with this email already exists.",
                "warning"
            )
            return redirect(url_for("login"))

        normalized_phone = None

        if phone:
            normalized_phone = normalize_phone(
                phone,
                "KE"
            )

            if not normalized_phone:
                flash(
                    "Please enter a valid phone number.",
                    "danger"
                )
                return render_template("register.html")

        allowed_currencies = [
            code
            for code, name in SUPPORTED_CURRENCIES
        ]

        if currency not in allowed_currencies:
            currency = "KES"

        user = User(
            full_name=full_name,
            email=email,
            phone=normalized_phone,
            country=country,
            currency=currency,
            password_hash=generate_password_hash(password),
            balance=Decimal("0.00")
        )

        db.session.add(user)
        db.session.commit()

        flash(
            "Your GlobalVest account has been created.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================

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

        if not user:
            flash(
                "Invalid email or password.",
                "danger"
            )
            return render_template("login.html")

        if not user.is_active:
            flash(
                "Your account has been disabled.",
                "danger"
            )
            return render_template("login.html")

        if not check_password_hash(
            user.password_hash,
            password
        ):
            flash(
                "Invalid email or password.",
                "danger"
            )
            return render_template("login.html")

        session.clear()

        session["user_id"] = user.id

        flash(
            "Welcome back to GlobalVest.",
            "success"
        )

        if user.is_admin:
            return redirect(url_for("admin"))

        return redirect(url_for("dashboard"))

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("index"))


# ============================================================
# USER DASHBOARD
# ============================================================

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
        item
        for item in investments
        if item.status == "active"
    ]

    total_invested = sum(
        (
            money(item.amount)
            for item in active_investments
        ),
        Decimal("0.00")
    )

    total_profit = sum(
        (
            investment_profit(item)
            for item in active_investments
        ),
        Decimal("0.00")
    )

    total_value = total_invested + total_profit

    recent_transactions = Transaction.query.filter_by(
        user_id=user.id
    ).order_by(
        Transaction.created_at.desc()
    ).limit(10).all()

    return render_template(
        "dashboard.html",
        user=user,
        investments=investments,
        active_investments=active_investments,
        total_invested=money(total_invested),
        total_profit=money(total_profit),
        total_value=money(total_value),
        recent_transactions=recent_transactions,
    )


# ============================================================
# CREATE INVESTMENT
# ============================================================

@app.route("/invest", methods=["GET", "POST"])
@login_required
def invest():

    user = current_user()

    if request.method == "POST":

        amount = money(
            request.form.get(
                "amount",
                "0"
            )
        )

        if amount <= Decimal("0.00"):
            flash(
                "Enter a valid investment amount.",
                "danger"
            )
            return render_template("invest.html")

        if money(user.balance) < amount:
            flash(
                "Insufficient wallet balance.",
                "danger"
            )
            return render_template(
    "invest.html",
    user=user
            )

        rate = get_daily_rate()

        start_date = utc_now()

        maturity_date = (
            start_date
            + timedelta(days=MATURITY_DAYS)
        )

        investment = Investment(
            user_id=user.id,
            amount=amount,
            daily_rate=rate,
            start_date=start_date,
            maturity_date=maturity_date,
            status="active"
        )

        user.balance = money(user.balance) - amount

        db.session.add(investment)

        create_transaction(
            user,
            "investment",
            -amount,
            "Investment created"
        )

        db.session.commit()

        flash(
            "Your investment has been created successfully.",
            "success"
        )

        return redirect(url_for("investments"))

    return render_template(
    "invest.html",
    user=user
        )


# ============================================================
# INVESTMENTS
# ============================================================

@app.route("/investments")
@login_required
def investments():

    user = current_user()

    user_investments = Investment.query.filter_by(
        user_id=user.id
    ).order_by(
        Investment.created_at.desc()
    ).all()

    investment_data = []

    for investment in user_investments:

        profit = investment_profit(
            investment
        )

        total_value = (
            money(investment.amount)
            + profit
        )

        investment_data.append({
            "investment": investment,
            "profit": profit,
            "total_value": total_value
        })

 return render_template(
    "invest.html",
    user=user
 )


# ============================================================
# DEPOSIT
# ============================================================

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():

    user = current_user()

    if request.method == "POST":

        amount = money(
            request.form.get(
                "amount",
                "0"
            )
        )

        method = request.form.get(
            "method",
            "M-Pesa"
        ).strip()

        if amount <= Decimal("0.00"):
            flash(
                "Enter a valid deposit amount.",
                "danger"
            )
            return render_template("deposit.html")

        # ----------------------------------------------------
        # M-PESA
        # ----------------------------------------------------

        if method.lower() in [
            "m-pesa",
            "mpesa",
            "m_pesa"
        ]:

            if not user.phone:
                flash(
                    "Please add your Kenyan phone number to your profile before using M-Pesa.",
                    "warning"
                )

                return redirect(
                    url_for("profile")
                )

            deposit_record = Deposit(
                user_id=user.id,
                amount=amount,
                method="M-Pesa",
                status="pending"
            )

            db.session.add(
                deposit_record
            )

            db.session.flush()

            result = initiate_mpesa_stk(
                user.phone,
                amount,
                deposit_record.reference,
                "GlobalVest wallet deposit"
            )

            if not result["success"]:

                db.session.delete(
                    deposit_record
                )

                db.session.commit()

                flash(
                    result.get(
                        "message",
                        "Unable to initiate M-Pesa payment."
                    ),
                    "danger"
                )

                return render_template(
                    "deposit.html"
                )

            response_data = result.get(
                "data",
                {}
            )

            deposit_record.checkout_request_id = (
                response_data.get(
                    "CheckoutRequestID"
                )
            )

            db.session.commit()

            flash(
                "M-Pesa payment request sent. Complete the payment on your phone.",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        # ----------------------------------------------------
        # OTHER PAYMENT METHODS
        # ----------------------------------------------------

        deposit_record = Deposit(
            user_id=user.id,
            amount=amount,
            method=method,
            status="pending"
        )

        db.session.add(
            deposit_record
        )

        db.session.commit()

        flash(
            "Your deposit request has been submitted and is awaiting verification.",
            "success"
        )

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "deposit.html"
    )


# ============================================================
# END OF PART 3
# ============================================================
# ============================================================
# PART 4 — WITHDRAWALS, TRANSACTIONS, CALLBACK & PROFILE
# ============================================================


# ============================================================
# WITHDRAW
# ============================================================

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():

    user = current_user()

    if request.method == "POST":

        amount = money(
            request.form.get(
                "amount",
                "0"
            )
        )

        method = request.form.get(
            "method",
            "M-Pesa"
        ).strip()

        account = request.form.get(
            "account",
            ""
        ).strip()

        if amount <= Decimal("0.00"):
            flash(
                "Enter a valid withdrawal amount.",
                "danger"
            )
            return render_template(
                "withdraw.html"
            )

        if money(user.balance) < amount:
            flash(
                "Insufficient wallet balance.",
                "danger"
            )
            return render_template(
                "withdraw.html"
            )

        if not account:
            flash(
                "Enter the account or phone number for the withdrawal.",
                "danger"
            )
            return render_template(
                "withdraw.html"
            )

        withdrawal = Withdrawal(
            user_id=user.id,
            amount=amount,
            method=method,
            account=account,
            status="pending"
        )

        # Reserve the requested amount while waiting
        # for administrator processing.
        user.balance = (
            money(user.balance)
            - amount
        )

        db.session.add(withdrawal)

        create_transaction(
            user,
            "withdrawal_hold",
            -amount,
            "Withdrawal request pending"
        )

        db.session.commit()

        flash(
            "Your withdrawal request has been submitted for review.",
            "success"
        )

        return redirect(
            url_for("transactions")
        )

    return render_template(
        "withdraw.html"
    )


# ============================================================
# TRANSACTIONS
# ============================================================

@app.route("/transactions")
@login_required
def transactions():

    user = current_user()

    transaction_list = Transaction.query.filter_by(
        user_id=user.id
    ).order_by(
        Transaction.created_at.desc()
    ).all()

    return render_template(
        "transactions.html",
        transactions=transaction_list
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    user = current_user()

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

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
            user.currency
        ).strip().upper()

        if not full_name:
            flash(
                "Full name cannot be empty.",
                "danger"
            )
            return render_template(
                "profile.html",
                user=user
            )

        if phone:

            normalized_phone = normalize_phone(
                phone,
                "KE"
            )

            if not normalized_phone:
                flash(
                    "Please enter a valid phone number.",
                    "danger"
                )

                return render_template(
                    "profile.html",
                    user=user
                )

            user.phone = normalized_phone

        else:
            user.phone = None

        allowed_currencies = [
            code
            for code, name in SUPPORTED_CURRENCIES
        ]

        if currency not in allowed_currencies:
            currency = "KES"

        user.full_name = full_name
        user.country = country
        user.currency = currency

        db.session.commit()

        flash(
            "Your profile has been updated.",
            "success"
        )

        return redirect(
            url_for("profile")
        )

    return render_template(
        "profile.html",
        user=user
    )


# ============================================================
# M-PESA CALLBACK
# ============================================================

@app.route(
    "/mpesa/callback",
    methods=["POST"]
)
def mpesa_callback():

    data = request.get_json(
        silent=True
    )

    if not data:
        return jsonify({
            "ResultCode": 1,
            "ResultDesc": "Invalid callback data"
        }), 400

    try:

        callback = (
            data
            .get("Body", {})
            .get("stkCallback", {})
        )

        checkout_id = callback.get(
            "CheckoutRequestID"
        )

        result_code = callback.get(
            "ResultCode"
        )

        result_desc = callback.get(
            "ResultDesc",
            ""
        )

        if not checkout_id:
            return jsonify({
                "ResultCode": 1,
                "ResultDesc": "Missing CheckoutRequestID"
            }), 400

        deposit_record = Deposit.query.filter_by(
            checkout_request_id=checkout_id
        ).first()

        if not deposit_record:

            # We acknowledge the callback without
            # creating money for an unknown request.
            return jsonify({
                "ResultCode": 0,
                "ResultDesc": "Callback received"
            })

        # ----------------------------------------------------
        # IDEMPOTENCY
        # ----------------------------------------------------

        if deposit_record.status == "completed":

            return jsonify({
                "ResultCode": 0,
                "ResultDesc": "Already processed"
            })

        # ----------------------------------------------------
        # PAYMENT FAILED / CANCELLED
        # ----------------------------------------------------

        if result_code != 0:

            deposit_record.status = "failed"

            db.session.commit()

            return jsonify({
                "ResultCode": 0,
                "ResultDesc": "Callback processed"
            })

        # ----------------------------------------------------
        # SUCCESSFUL PAYMENT
        # ----------------------------------------------------

        metadata = (
            callback
            .get("CallbackMetadata", {})
            .get("Item", [])
        )

        metadata_map = {}

        for item in metadata:

            name = item.get("Name")

            if name:
                metadata_map[name] = item.get(
                    "Value"
                )

        receipt = metadata_map.get(
            "MpesaReceiptNumber"
        )

        paid_amount = money(
            metadata_map.get(
                "Amount",
                "0"
            )
        )

        # ----------------------------------------------------
        # VERIFY AMOUNT
        # ----------------------------------------------------

        expected_amount = money(
            deposit_record.amount
        )

        if paid_amount != expected_amount:

            deposit_record.status = "review"

            db.session.commit()

            return jsonify({
                "ResultCode": 0,
                "ResultDesc": "Payment requires review"
            })

        # ----------------------------------------------------
        # PREVENT RECEIPT DUPLICATION
        # ----------------------------------------------------

        if receipt:

            existing_receipt = Deposit.query.filter(
                Deposit.mpesa_receipt == receipt,
                Deposit.id != deposit_record.id
            ).first()

            if existing_receipt:

                deposit_record.status = "review"

                db.session.commit()

                return jsonify({
                    "ResultCode": 0,
                    "ResultDesc": "Duplicate receipt"
                })

        # ----------------------------------------------------
        # CREDIT WALLET
        # ----------------------------------------------------

        user = deposit_record.user

        user.balance = (
            money(user.balance)
            + paid_amount
        )

        deposit_record.status = "completed"
        deposit_record.mpesa_receipt = receipt

        create_transaction(
            user,
            "deposit",
            paid_amount,
            "M-Pesa wallet deposit"
        )

        db.session.commit()

        return jsonify({
            "ResultCode": 0,
            "ResultDesc": "Payment processed successfully"
        })

    except Exception:

        db.session.rollback()

        return jsonify({
            "ResultCode": 1,
            "ResultDesc": "Callback processing error"
        }), 500


# ============================================================
# CURRENT USER API
# ============================================================

@app.route("/api/me")
@login_required
def api_me():

    user = current_user()

    return jsonify({
        "id": user.id,
        "public_id": user.public_id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "country": user.country,
        "currency": user.currency,
        "balance": float(
            money(user.balance)
        ),
        "is_admin": user.is_admin
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok",
        "platform": PLATFORM_NAME
    })


# ============================================================
# END OF PART 4
# ============================================================
# ============================================================
# PART 5 — ADMIN CONTROL CENTER
# ============================================================


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin")
@admin_required
def admin():

    users = User.query.order_by(
        User.created_at.desc()
    ).all()

    deposits = Deposit.query.order_by(
        Deposit.created_at.desc()
    ).limit(50).all()

    withdrawals = Withdrawal.query.order_by(
        Withdrawal.created_at.desc()
    ).limit(50).all()

    investments = Investment.query.order_by(
        Investment.created_at.desc()
    ).limit(50).all()

    payment_accounts = PaymentAccount.query.order_by(
        PaymentAccount.created_at.desc()
    ).all()

    total_users = User.query.count()

    pending_deposits = Deposit.query.filter_by(
        status="pending"
    ).count()

    pending_withdrawals = Withdrawal.query.filter_by(
        status="pending"
    ).count()

    total_deposited = sum(
        (
            money(d.amount)
            for d in Deposit.query.filter_by(
                status="completed"
            ).all()
        ),
        Decimal("0.00")
    )

    total_invested = sum(
        (
            money(i.amount)
            for i in Investment.query.filter_by(
                status="active"
            ).all()
        ),
        Decimal("0.00")
    )

    return render_template(
        "admin.html",
        users=users,
        deposits=deposits,
        withdrawals=withdrawals,
        investments=investments,
        payment_accounts=payment_accounts,
        total_users=total_users,
        pending_deposits=pending_deposits,
        pending_withdrawals=pending_withdrawals,
        total_deposited=money(total_deposited),
        total_invested=money(total_invested),
        daily_rate=get_daily_rate()
    )


# ============================================================
# CHANGE DAILY RATE
# ============================================================

@app.route(
    "/admin/settings",
    methods=["POST"]
)
@admin_required
def admin_settings():

    rate = money(
        request.form.get(
            "daily_rate",
            str(DEFAULT_DAILY_GROWTH_RATE)
        )
    )

    if rate < Decimal("0.00"):
        flash(
            "Daily rate cannot be negative.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    set_setting(
        "daily_growth_rate",
        rate
    )

    flash(
        "Platform growth setting updated.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# ENABLE / DISABLE USER
# ============================================================

@app.route(
    "/admin/user/<int:user_id>/toggle",
    methods=["POST"]
)
@admin_required
def admin_toggle_user(user_id):

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        flash(
            "User not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    if user.is_admin:

        flash(
            "Administrator accounts cannot be disabled here.",
            "warning"
        )

        return redirect(
            url_for("admin")
        )

    user.is_active = not user.is_active

    db.session.commit()

    status = (
        "activated"
        if user.is_active
        else "disabled"
    )

    flash(
        f"User account {status}.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# APPROVE DEPOSIT
# ============================================================

@app.route(
    "/admin/deposit/<int:deposit_id>/approve",
    methods=["POST"]
)
@admin_required
def admin_approve_deposit(deposit_id):

    deposit_record = db.session.get(
        Deposit,
        deposit_id
    )

    if not deposit_record:

        flash(
            "Deposit not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    if deposit_record.status != "pending":

        flash(
            "This deposit has already been processed.",
            "warning"
        )

        return redirect(
            url_for("admin")
        )

    user = deposit_record.user
    amount = money(
        deposit_record.amount
    )

    user.balance = (
        money(user.balance)
        + amount
    )

    deposit_record.status = "completed"

    create_transaction(
        user,
        "deposit",
        amount,
        f"Deposit approved: {deposit_record.reference}"
    )

    db.session.commit()

    flash(
        "Deposit approved and wallet credited.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# REJECT DEPOSIT
# ============================================================

@app.route(
    "/admin/deposit/<int:deposit_id>/reject",
    methods=["POST"]
)
@admin_required
def admin_reject_deposit(deposit_id):

    deposit_record = db.session.get(
        Deposit,
        deposit_id
    )

    if not deposit_record:

        flash(
            "Deposit not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    if deposit_record.status != "pending":

        flash(
            "This deposit has already been processed.",
            "warning"
        )

        return redirect(
            url_for("admin")
        )

    deposit_record.status = "rejected"

    db.session.commit()

    flash(
        "Deposit rejected.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# APPROVE WITHDRAWAL
# ============================================================

@app.route(
    "/admin/withdrawal/<int:withdrawal_id>/approve",
    methods=["POST"]
)
@admin_required
def admin_approve_withdrawal(withdrawal_id):

    withdrawal = db.session.get(
        Withdrawal,
        withdrawal_id
    )

    if not withdrawal:

        flash(
            "Withdrawal not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    if withdrawal.status != "pending":

        flash(
            "This withdrawal has already been processed.",
            "warning"
        )

        return redirect(
            url_for("admin")
        )

    withdrawal.status = "completed"

    create_transaction(
        withdrawal.user,
        "withdrawal",
        Decimal("0.00"),
        f"Withdrawal processed: {withdrawal.reference}"
    )

    db.session.commit()

    flash(
        "Withdrawal marked as completed.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# REJECT WITHDRAWAL
# ============================================================

@app.route(
    "/admin/withdrawal/<int:withdrawal_id>/reject",
    methods=["POST"]
)
@admin_required
def admin_reject_withdrawal(withdrawal_id):

    withdrawal = db.session.get(
        Withdrawal,
        withdrawal_id
    )

    if not withdrawal:

        flash(
            "Withdrawal not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    if withdrawal.status != "pending":

        flash(
            "This withdrawal has already been processed.",
            "warning"
        )

        return redirect(
            url_for("admin")
        )

    user = withdrawal.user
    amount = money(
        withdrawal.amount
    )

    # Return reserved funds to wallet.
    user.balance = (
        money(user.balance)
        + amount
    )

    withdrawal.status = "rejected"

    create_transaction(
        user,
        "withdrawal_reversal",
        amount,
        f"Withdrawal rejected: {withdrawal.reference}"
    )

    db.session.commit()

    flash(
        "Withdrawal rejected and funds returned to the wallet.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# ADD PAYMENT ACCOUNT
# ============================================================

@app.route(
    "/admin/payment-account/add",
    methods=["POST"]
)
@admin_required
def admin_add_payment_account():

    country = request.form.get(
        "country",
        ""
    ).strip()

    method = request.form.get(
        "method",
        ""
    ).strip()

    account_name = request.form.get(
        "account_name",
        ""
    ).strip()

    account_number = request.form.get(
        "account_number",
        ""
    ).strip()

    currency = request.form.get(
        "currency",
        "KES"
    ).strip().upper()

    if not country or not method:
        flash(
            "Country and payment method are required.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    if not account_name or not account_number:
        flash(
            "Account name and account number are required.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    account = PaymentAccount(
        country=country,
        method=method,
        account_name=account_name,
        account_number=account_number,
        currency=currency,
        is_active=True
    )

    db.session.add(account)
    db.session.commit()

    flash(
        "Payment account added.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# TOGGLE PAYMENT ACCOUNT
# ============================================================

@app.route(
    "/admin/payment-account/<int:account_id>/toggle",
    methods=["POST"]
)
@admin_required
def admin_toggle_payment_account(account_id):

    account = db.session.get(
        PaymentAccount,
        account_id
    )

    if not account:

        flash(
            "Payment account not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    account.is_active = not account.is_active

    db.session.commit()

    flash(
        "Payment account status updated.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# DELETE PAYMENT ACCOUNT
# ============================================================

@app.route(
    "/admin/payment-account/<int:account_id>/delete",
    methods=["POST"]
)
@admin_required
def admin_delete_payment_account(account_id):

    account = db.session.get(
        PaymentAccount,
        account_id
    )

    if not account:

        flash(
            "Payment account not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    db.session.delete(account)
    db.session.commit()

    flash(
        "Payment account deleted.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# ============================================================
# END OF PART 5
# ============================================================
# ============================================================
# PART 6 — DATABASE INITIALIZATION & STARTUP
# ============================================================


def create_admin_account():
    """
    Create the administrator account from environment variables
    if it does not already exist.
    """

    admin_email = os.getenv(
        "ADMIN_EMAIL",
        ""
    ).strip().lower()

    admin_password = os.getenv(
        "ADMIN_PASSWORD",
        ""
    )

    if not admin_email or not admin_password:
        return

    admin = User.query.filter_by(
        email=admin_email
    ).first()

    if admin:
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()

        return

    admin = User(
        full_name="GlobalVest Administrator",
        email=admin_email,
        password_hash=generate_password_hash(
            admin_password
        ),
        currency="KES",
        is_admin=True,
        is_active=True
    )

    db.session.add(admin)
    db.session.commit()


def initialize_database():
    """
    Create database tables and initialize the administrator.
    """

    db.create_all()

    create_admin_account()


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "index.html"
    ), 404


@app.errorhandler(500)
def internal_server_error(error):

    db.session.rollback()

    return (
        "GlobalVest encountered a server error.",
        500
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

with app.app_context():
    initialize_database()


# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        ),
        debug=False
    )


# ============================================================
# END OF APP.PY
# ============================================================
