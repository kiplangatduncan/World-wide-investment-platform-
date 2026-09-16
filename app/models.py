from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


# ============================================================
# USER
# ============================================================

class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(30),
        unique=True,
        nullable=True
    )

    country = db.Column(
        db.String(80),
        nullable=True
    )

    currency = db.Column(
        db.String(10),
        default="KES"
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    balance = db.Column(
        db.Float,
        default=0.0
    )

    total_deposited = db.Column(
        db.Float,
        default=0.0
    )

    total_invested = db.Column(
        db.Float,
        default=0.0
    )

    total_withdrawn = db.Column(
        db.Float,
        default=0.0
    )

    referral_code = db.Column(
        db.String(50),
        unique=True,
        nullable=True
    )

    referred_by = db.Column(
        db.String(50),
        nullable=True
    )

    is_admin = db.Column(
        db.Boolean,
        default=False
    )

    is_active_user = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # --------------------------------------------------------
    # PASSWORD
    # --------------------------------------------------------

    def set_password(self, password):

        self.password_hash = generate_password_hash(
            password
        )

    def check_password(self, password):

        return check_password_hash(
            self.password_hash,
            password
        )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    def __repr__(self):

        return (
            f"<User {self.username}>"
        )


# ============================================================
# INVESTMENT PLAN
# ============================================================

class InvestmentPlan(db.Model):

    __tablename__ = "investment_plans"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    minimum_amount = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    maximum_amount = db.Column(
        db.Float,
        nullable=True
    )

    duration_days = db.Column(
        db.Integer,
        nullable=False,
        default=30
    )

    return_rate = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    investments = db.relationship(
        "Investment",
        backref="plan",
        lazy=True
    )

    def __repr__(self):

        return (
            f"<InvestmentPlan {self.name}>"
        )


# ============================================================
# INVESTMENT
# ============================================================

class Investment(db.Model):

    __tablename__ = "investments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    plan_id = db.Column(
        db.Integer,
        db.ForeignKey("investment_plans.id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    expected_return = db.Column(
        db.Float,
        default=0.0
    )

    status = db.Column(
        db.String(30),
        default="active"
    )

    start_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    maturity_date = db.Column(
        db.DateTime,
        nullable=True
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "investments",
            lazy=True
        )
    )

    def __repr__(self):

        return (
            f"<Investment {self.id}>"
        )


# ============================================================
# DEPOSIT
# ============================================================

class Deposit(db.Model):

    __tablename__ = "deposits"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        default="KES"
    )

    payment_method = db.Column(
        db.String(50),
        nullable=False
    )

    provider = db.Column(
        db.String(100),
        nullable=True
    )

    reference = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "deposits",
            lazy=True
        )
    )

    def __repr__(self):

        return (
            f"<Deposit {self.reference}>"
        )


# ============================================================
# WITHDRAWAL
# ============================================================

class Withdrawal(db.Model):

    __tablename__ = "withdrawals"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        default="KES"
    )

    payment_method = db.Column(
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

    reference = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="pending"
    )

    admin_note = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    processed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "withdrawals",
            lazy=True
        )
    )

    def __repr__(self):

        return (
            f"<Withdrawal {self.reference}>"
        )


# ============================================================
# TRANSACTION
# ============================================================

class Transaction(db.Model):

    __tablename__ = "transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    transaction_type = db.Column(
        db.String(50),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        default="KES"
    )

    reference = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        default="completed"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "transactions",
            lazy=True
        )
    )

    def __repr__(self):

        return (
            f"<Transaction {self.reference}>"
        )


# ============================================================
# PAYMENT ACCOUNT
# ============================================================

class PaymentAccount(db.Model):

    __tablename__ = "payment_accounts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    country = db.Column(
        db.String(80),
        nullable=False
    )

    currency = db.Column(
        db.String(10),
        nullable=False
    )

    payment_method = db.Column(
        db.String(80),
        nullable=False
    )

    provider = db.Column(
        db.String(100),
        nullable=True
    )

    account_name = db.Column(
        db.String(150),
        nullable=True
    )

    account_number = db.Column(
        db.String(150),
        nullable=True
    )

    phone_number = db.Column(
        db.String(50),
        nullable=True
    )

    branch = db.Column(
        db.String(100),
        nullable=True
    )

    additional_details = db.Column(
        db.Text,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):

        return (
            f"<PaymentAccount "
            f"{self.country} "
            f"{self.payment_method}>"
        )


# ============================================================
# REFERRAL
# ============================================================

class Referral(db.Model):

    __tablename__ = "referrals"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    referrer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    referred_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    bonus_amount = db.Column(
        db.Float,
        default=0.0
    )

    status = db.Column(
        db.String(30),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    referrer = db.relationship(
        "User",
        foreign_keys=[referrer_id],
        backref=db.backref(
            "referrals_made",
            lazy=True
        )
    )

    referred_user = db.relationship(
        "User",
        foreign_keys=[referred_user_id],
        backref=db.backref(
            "referred_by_user",
            lazy=True
        )
    )

    def __repr__(self):

        return (
            f"<Referral {self.id}>"
        )


# ============================================================
# PLATFORM SETTINGS
# ============================================================

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

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):

        return (
            f"<PlatformSetting "
            f"{self.setting_key}>"
  )
