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
from app.mpesa import mpesa_bp
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)


# ============================================================
# GLOBALVEST CONFIGURATION
# ============================================================

load_dotenv()

app = Flask(__name__)
app.register_blueprint(mpesa_bp)

@app.route("/mpesa")
def mpesa():
    return "M-Pesa route is working"


app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "CHANGE-ME-IN-PRODUCTION"
)

database_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///investment_platform.db"
)

# Render may provide postgres://
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

# Platform-configured calculation.
# This is NOT a guaranteed investment return.
DEFAULT_DAILY_GROWTH_RATE = Decimal("2.0")

MATURITY_DAYS = 4


# ============================================================
# BASIC HELPERS
# ============================================================

def utc_now():
    """Return the current UTC time."""
    return datetime.utcnow()


def money(value):
    """Safely convert a value to two-decimal Decimal money."""
    try:
        return Decimal(str(value)).quantize(
            Decimal("0.01")
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError
    ):
        return Decimal("0.00")


def generate_public_id():
    return str(uuid.uuid4())


# ============================================================
# USER MODEL
# ============================================================

class User(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

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
        default=lambda:
            "DEP-" + uuid.uuid4().hex[:12].upper()
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
        default=lambda:
            "INV-" + uuid.uuid4().hex[:12].upper()
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
        default=lambda:
            "WDR-" + uuid.uuid4().hex[:12].upper()
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
        default=lambda:
            "TX-" + uuid.uuid4().hex[:12].upper()
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
# CURRENT USER
# ============================================================

def current_user():

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return None

    return db.session.get(
        User,
        user_id
    )


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        user = current_user()

        if not user:

            flash(
                "Please log in to continue.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        if not user.is_active:

            session.clear()

            flash(
                "Your account has been disabled.",
                "danger"
            )

            return redirect(
                url_for("login")
            )

        return view(
            *args,
            **kwargs
        )

    return wrapped


# ============================================================
# PLATFORM SETTINGS HELPERS
# ============================================================

def get_setting(
    key,
    default=None
):

    setting = PlatformSetting.query.filter_by(
        key=key
    ).first()

    if setting:
        return setting.value

    return default


def set_setting(
    key,
    value
):

    setting = PlatformSetting.query.filter_by(
        key=key
    ).first()

    if not setting:

        setting = PlatformSetting(
            key=key
        )

        db.session.add(
            setting
        )

    setting.value = str(value)

    db.session.commit()

    return setting


def get_daily_rate():

    value = get_setting(
        "daily_growth_rate",
        str(DEFAULT_DAILY_GROWTH_RATE)
    )

    return money(value)


# ============================================================
# INVESTMENT CALCULATIONS
# ============================================================

def investment_profit(
    investment
):

    """
    Calculate simple daily growth using the platform's
    configured rate.

    This is a platform calculation and is NOT a guarantee
    of investment returns.
    """

    if investment.status != "active":
        return Decimal("0.00")

    today = utc_now()

    if today <= investment.start_date:
        return Decimal("0.00")

    end_date = min(
        today,
        investment.maturity_date
    )

    elapsed_seconds = (
        end_date - investment.start_date
    ).total_seconds()

    days = int(
        elapsed_seconds // 86400
    )

    if days <= 0:
        return Decimal("0.00")

    rate = money(
        investment.daily_rate
    )

    profit = (
        money(investment.amount)
        * rate
        * Decimal(days)
        / Decimal("100")
    )

    return money(
        profit
    )


def investment_total_value(
    investment
):

    return money(
        investment.amount
        + investment_profit(investment)
    )


# ============================================================
# TRANSACTION HELPER
# ============================================================

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

    db.session.add(
        transaction
    )

    return transaction


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

        name = getattr(
            country,
            "name",
            None
        )

        if name:
            countries.append(
                name
            )

    return sorted(
        set(countries)
    )


def get_currencies():

    return SUPPORTED_CURRENCIES


# ============================================================
# PHONE NUMBER HELPERS
# ============================================================

def normalize_phone(
    phone,
    country="KE"
):

    if not phone:
        return None

    phone = str(
        phone
    ).strip()

    try:

        parsed = phonenumbers.parse(
            phone,
            country
        )

        if not phonenumbers.is_valid_number(
            parsed
        ):
            return None

        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )

    except Exception:

        return None


def mpesa_phone(
    phone
):

    """
    Convert a Kenyan phone number into the format
    normally expected by the Daraja API.
    """

    normalized = normalize_phone(
        phone,
        "KE"
    )

    if not normalized:
        return None

    number = normalized.replace(
        "+",
        ""
    )

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

def initiate_stk_push(phone, amount, account_reference="GlobalVest"):
    if not MPESA_CALLBACK_URL:
        return {
            "success": False,
            "message": "M-Pesa callback URL is not configured."
        }

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    password = mpesa_password(timestamp)

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": "GlobalVest Investment"
    }

    headers = {
        "Authorization": f"Bearer {get_mpesa_token()}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            MPESA_STK_URL,
            json=payload,
            headers=headers,
            timeout=30
        )

        return response.json()

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
    }


def mpesa_base_url():

    if MPESA_ENVIRONMENT == "production":

        return (
            "https://api.safaricom.co.ke"
        )

    return (
        "https://sandbox.safaricom.co.ke"
    )


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
        "Authorization":
            "Basic " + encoded
    }

    url = (
        mpesa_base_url()
        + "/oauth/v1/generate"
        "?grant_type=client_credentials"
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "access_token"
        )

    except Exception:

        return None


def mpesa_password(
    timestamp
):

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

    A successful API response only means Safaricom
    accepted the request.

    The wallet must NOT be credited until the callback
    reports ResultCode == 0.
    """

    token = mpesa_access_token()

    if not token:

        return {
            "success": False,
            "message":
                "M-Pesa credentials are not configured."
        }

    phone_number = mpesa_phone(
        phone
    )

    if not phone_number:

        return {
            "success": False,
            "message":
                "Enter a valid Kenyan M-Pesa number."
        }

    if not MPESA_SHORTCODE:

        return {
            "success": False,
            "message":
                "M-Pesa shortcode is not configured."
        }

    if not MPESA_PASSKEY:

        return {
            "success": False,
            "message":
                "M-Pesa passkey is not configured."
        }

    if not MPESA_CALLBACK_URL:

        return {
            "success": False,
            "message":
                "M-Pesa callback URL is not configured."
        }

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d%H%M%S"
    )

    password = mpesa_password(
        timestamp
    )
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
        "TransactionDesc": "GlobalVest Deposit",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        data = response.json()

        if (
            response.ok
            and data.get("ResponseCode") == "0"
        ):
            return {
                "success": True,
                "data": data,
            }

        return {
            "success": False,
            "message": data.get(
                "errorMessage",
                data.get(
                    "ResponseDescription",
                    "M-Pesa request failed."
                )
            ),
            "data": data,
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"M-Pesa connection error: {str(e)}",
        }

    except ValueError:
        return {
            "success": False,
            "message": "M-Pesa returned an invalid response.",
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"M-Pesa error: {str(e)}",
        }
