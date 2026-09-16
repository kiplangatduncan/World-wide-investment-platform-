import os


class Config:

    # --------------------------------------------------
    # APPLICATION
    # --------------------------------------------------

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-change-me"
    )

    APP_NAME = os.getenv(
        "APP_NAME",
        "Investment Platform"
    )

    APP_URL = os.getenv(
        "APP_URL",
        ""
    )


    # --------------------------------------------------
    # DATABASE
    # --------------------------------------------------

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "sqlite:///investment_platform.db"
    )

    SQLALCHEMY_DATABASE_URI = DATABASE_URL

    SQLALCHEMY_TRACK_MODIFICATIONS = False


    # --------------------------------------------------
    # M-PESA / SAFARICOM DARAJA
    # --------------------------------------------------

    MPESA_ENVIRONMENT = os.getenv(
        "MPESA_ENVIRONMENT",
        "sandbox"
    )

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


    # --------------------------------------------------
    # FLUTTERWAVE
    # --------------------------------------------------

    FLUTTERWAVE_PUBLIC_KEY = os.getenv(
        "FLUTTERWAVE_PUBLIC_KEY",
        ""
    )

    FLUTTERWAVE_SECRET_KEY = os.getenv(
        "FLUTTERWAVE_SECRET_KEY",
        ""
    )

    FLUTTERWAVE_ENCRYPTION_KEY = os.getenv(
        "FLUTTERWAVE_ENCRYPTION_KEY",
        ""
    )

    FLUTTERWAVE_REDIRECT_URL = os.getenv(
        "FLUTTERWAVE_REDIRECT_URL",
        ""
    )


    # --------------------------------------------------
    # ADMIN
    # --------------------------------------------------

    ADMIN_EMAIL = os.getenv(
        "ADMIN_EMAIL",
        ""
    )

    ADMIN_PASSWORD = os.getenv(
        "ADMIN_PASSWORD",
        ""  
    )
