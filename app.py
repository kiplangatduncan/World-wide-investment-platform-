import os
import uuid
import base64
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
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
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# APP
# ============================================================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "CHANGE-THIS-SECRET-KEY-IN-RENDER"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Secure cookies when deployed over HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

if os.getenv("FLASK_ENV", "production").lower() == "production":
    app.config["SESSION_COOKIE_SECURE"] = True


# ============================================================
# DATABASE
# ============================================================

database_url = os.getenv(
    "DATABASE_URL",
    "sqlite:///investment_platform.db"
)

# Render/Postgres may provide postgres://
if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url

db = SQLAlchemy(app)


# ============================================================
# PLATFORM CONFIGURATION
# ============================================================

PLATFORM_NAME = "GlobalVest"

# This is a software/display setting.
# It must NOT be presented to customers as a guaranteed return.
DEFAULT_DAILY_GROWTH_RATE = Decimal(
    os.getenv("DEFAULT_DAILY_GROWTH_RATE", "2.0")
)

DEFAULT_MATURITY_DAYS = int(
    os.getenv("MATURITY_DAYS", "4")
)

DEFAULT_CURRENCY = "KES"


# ============================================================
# MPESA CONFIGURATION
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


if MPESA_ENVIRONMENT == "production":
    MPESA_BASE_URL = "https://api.safaricom.co.ke"
else:
    MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"


# ============================================================
# DATABASE MODELS
# ============================================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )

    full_name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
        index=True
    )

    phone = db.Column(
        db.String(30),
        nullable=False
    )

    country = db.Column(
        db.String(100),
        nullable=False,
        default="Kenya"
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default=DEFAULT_CURRENCY
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
        nullable=False,
        default=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    deposits = db.relationship(
        "Deposit",
        backref="user",
        lazy=True
    )

    investments = db.relationship(
        "Investment",
        backref="user",
        lazy=True
    )

    withdrawals = db.relationship(
        "Withdrawal",
        backref="user",
        lazy=True
    )

    transactions = db.relationship(
        "Transaction",
        backref="user",
        lazy=True
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )


class Deposit(db.Model):
    __tablename__ = "deposits"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    reference = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        default=lambda: f"DEP-{uuid.uuid4().hex[:12].upper()}"
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="KES"
    )

    method = db.Column(
        db.String(50),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending",
        index=True
    )

    phone_number = db.Column(
        db.String(30),
        nullable=True
    )

    checkout_request_id = db.Column(
        db.String(150),
        unique=True,
        nullable=True,
        index=True
    )

    merchant_request_id = db.Column(
        db.String(150),
        nullable=True
    )

    mpesa_receipt = db.Column(
        db.String(100),
        nullable=True,
        index=True
    )

    transaction_id = db.Column(
        db.String(150),
        nullable=True
    )

    external_reference = db.Column(
        db.String(150),
        nullable=True
    )

    admin_note = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )


class Investment(db.Model):
    __tablename__ = "investments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="KES"
    )

    daily_rate = db.Column(
        db.Numeric(10, 4),
        nullable=False
    )

    maturity_days = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="active"
    )

    started_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    maturity_date = db.Column(
        db.DateTime,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class Withdrawal(db.Model):
    __tablename__ = "withdrawals"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    reference = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
        default=lambda: f"WDR-{uuid.uuid4().hex[:12].upper()}"
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="KES"
    )

    method = db.Column(
        db.String(50),
        nullable=False
    )

    destination = db.Column(
        db.String(255),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="pending"
    )

    admin_note = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    processed_at = db.Column(
        db.DateTime,
        nullable=True
    )


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    reference = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        default=lambda: f"TX-{uuid.uuid4().hex[:14].upper()}"
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    transaction_type = db.Column(
        db.String(40),
        nullable=False
    )

    amount = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    balance_before = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    balance_after = db.Column(
        db.Numeric(18, 2),
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="KES"
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="completed"
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    external_reference = db.Column(
        db.String(150),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class PaymentAccount(db.Model):
    __tablename__ = "payment_accounts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    method = db.Column(
        db.String(50),
        nullable=False
    )

    account_name = db.Column(
        db.String(150),
        nullable=True
    )

    account_number = db.Column(
        db.String(150),
        nullable=True
    )

    bank_name = db.Column(
        db.String(150),
        nullable=True
    )

    instructions = db.Column(
        db.Text,
        nullable=True
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="KES"
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class PlatformSetting(db.Model):
    __tablename__ = "platform_settings"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    setting_key = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    setting_value = db.Column(
        db.Text,
        nullable=True
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def utc_now():
    return datetime.utcnow()


def money(value):
    try:
        return Decimal(str(value)).quantize(
            Decimal("0.01")
        )
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def get_setting(key, default=None):
    setting = PlatformSetting.query.filter_by(
        setting_key=key
    ).first()

    if setting:
        return setting.setting_value

    return default


def set_setting(key, value):
    setting = PlatformSetting.query.filter_by(
        setting_key=key
    ).first()

    if setting is None:
        setting = PlatformSetting(
            setting_key=key,
            setting_value=str(value)
        )
        db.session.add(setting)
    else:
        setting.setting_value = str(value)

    return setting


def get_daily_rate():
    value = get_setting(
        "daily_growth_rate",
        str(DEFAULT_DAILY_GROWTH_RATE)
    )

    try:
        return Decimal(str(value))
    except InvalidOperation:
        return DEFAULT_DAILY_GROWTH_RATE


def get_maturity_days():
    value = get_setting(
        "maturity_days",
        str(DEFAULT_MATURITY_DAYS)
    )

    try:
        return int(value)
    except ValueError:
        return DEFAULT_MATURITY_DAYS


def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()

        if user is None or not user.is_active:
            session.clear()
            flash(
                "Please log in to continue.",
                "warning"
            )
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()

        if user is None or not user.is_active:
            session.clear()
            flash(
                "Please log in to continue.",
                "warning"
            )
            return redirect(url_for("login"))

        if not user.is_admin:
            flash(
                "Administrator access is required.",
                "danger"
            )
            return redirect(url_for("dashboard"))

        return view(*args, **kwargs)

    return wrapped


def normalize_phone(phone, country_code="KE"):
    phone = (phone or "").strip()

    if not phone:
        raise ValueError("Phone number is required.")

    try:
        parsed = phonenumbers.parse(
            phone,
            country_code
        )

        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(
                "Please enter a valid phone number."
            )

        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )

    except phonenumbers.NumberParseException:
        raise ValueError(
            "Please enter a valid phone number."
        )


def phone_to_mpesa(phone):
    """
    Converts E.164 phone numbers into 2547XXXXXXXX format.
    """

    cleaned = "".join(
        character
        for character in str(phone)
        if character.isdigit()
    )

    if cleaned.startswith("254"):
        return cleaned

    if cleaned.startswith("0"):
        return "254" + cleaned[1:]

    if cleaned.startswith("7") and len(cleaned) == 9:
        return "254" + cleaned

    if cleaned.startswith("1") and len(cleaned) == 9:
        return "254" + cleaned

    return cleaned


def get_countries():
    countries = []

    for country in pycountry.countries:
        name = getattr(
            country,
            "name",
            ""
        )

        alpha2 = getattr(
            country,
            "alpha_2",
            ""
        )

        if name and alpha2:
            countries.append({
                "name": name,
                "code": alpha2
            })

    countries.sort(
        key=lambda item: item["name"]
    )

    return countries


def supported_currencies():
    """
    Curated currency list for the platform interface.

    Availability of actual payment rails is separate from
    displaying a currency.
    """

    return [
        "AED",
        "AUD",
        "CAD",
        "CHF",
        "CNY",
        "DKK",
        "EUR",
        "GBP",
        "GHS",
        "INR",
        "JPY",
        "KES",
        "NGN",
        "NOK",
        "RWF",
        "SEK",
        "TZS",
        "UGX",
        "USD",
        "ZAR",
    ]


def add_transaction(
    user,
    transaction_type,
    amount,
    balance_before,
    balance_after,
    description="",
    external_reference=None,
    status="completed"
):
    transaction = Transaction(
        user_id=user.id,
        transaction_type=transaction_type,
        amount=money(amount),
        balance_before=money(balance_before),
        balance_after=money(balance_after),
        currency=user.currency or DEFAULT_CURRENCY,
        description=description,
        external_reference=external_reference,
        status=status
    )

    db.session.add(transaction)

    return transaction


# ============================================================
# MPESA FUNCTIONS
# ============================================================

def mpesa_credentials_ready():
    return bool(
        MPESA_CONSUMER_KEY
        and MPESA_CONSUMER_SECRET
        and MPESA_SHORTCODE
        and MPESA_PASSKEY
    )


def get_mpesa_access_token():
    if not MPESA_CONSUMER_KEY:
        raise RuntimeError(
            "MPESA_CONSUMER_KEY is not configured."
        )

    if not MPESA_CONSUMER_SECRET:
        raise RuntimeError(
            "MPESA_CONSUMER_SECRET is not configured."
        )

    url = (
        f"{MPESA_BASE_URL}"
        "/oauth/v1/generate"
        "?grant_type=client_credentials"
    )

    response = requests.get(
        url,
        auth=(
            MPESA_CONSUMER_KEY,
            MPESA_CONSUMER_SECRET
        ),
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    token = data.get("access_token")

    if not token:
        raise RuntimeError(
            "M-Pesa did not return an access token."
        )

    return token


def create_mpesa_password(timestamp):
    raw = (
        f"{MPESA_SHORTCODE}"
        f"{MPESA_PASSKEY}"
        f"{timestamp}"
    )

    encoded = base64.b64encode(
        raw.encode("utf-8")
    ).decode("utf-8")

    return encoded


def initiate_mpesa_stk(
    phone_number,
    amount,
    account_reference,
    transaction_description
):
    if not mpesa_credentials_ready():
        raise RuntimeError(
            "M-Pesa is not fully configured. "
            "Add the Daraja credentials in Render Environment Variables."
        )

    if not MPESA_CALLBACK_URL:
        raise RuntimeError(
            "MPESA_CALLBACK_URL is not configured."
        )

    token = get_mpesa_access_token()

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d%H%M%S")

    password = create_mpesa_password(
        timestamp
    )

    mpesa_phone = phone_to_mpesa(
        phone_number
    )

    payload = {
        "BusinessShortCode": MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(money(amount))),
        "PartyA": mpesa_phone,
        "PartyB": MPESA_SHORTCODE,
        "PhoneNumber": mpesa_phone,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_description,
    }

    url = (
        f"{MPESA_BASE_URL}"
        "/mpesa/stkpush/v1/processrequest"
    )

    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# TEMPLATE GLOBALS
# ============================================================

@app.context_processor
def inject_globals():
    user = current_user()

    return {
        "platform_name": PLATFORM_NAME,
        "current_user": user,
        "daily_rate": get_daily_rate(),
        "maturity_days": get_mat
