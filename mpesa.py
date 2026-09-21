import os
import base64
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime

import requests
import phonenumbers

from flask import Blueprint, request, jsonify


# ============================================================
# M-PESA BLUEPRINT
# ============================================================

mpesa_bp = Blueprint("mpesa", __name__)


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


# ============================================================
# BASE URL
# ============================================================

def mpesa_base_url():

    if MPESA_ENVIRONMENT == "production":

        return "https://api.safaricom.co.ke"

    return "https://sandbox.safaricom.co.ke"


# ============================================================
# ACCESS TOKEN
# ============================================================

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
        + "/oauth/v1/generate"
        + "?grant_type=client_credentials"
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


# ============================================================
# PHONE NUMBER
# ============================================================

def mpesa_phone(phone):

    """
    Convert Kenyan phone number to 254XXXXXXXXX.
    """

    if not phone:
        return None

    try:

        parsed = phonenumbers.parse(
            str(phone),
            "KE"
        )

        if not phonenumbers.is_valid_number(
            parsed
        ):
            return None

        formatted = phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )

        number = formatted.replace(
            "+",
            ""
        )

        if number.startswith("254"):

            return number

        return None

    except Exception:

        return None


# ============================================================
# PASSWORD
# ============================================================

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


# ============================================================
# STK PUSH
# ============================================================

def initiate_mpesa_stk(
    phone,
    amount,
    account_reference="GlobalVest",
    description="GlobalVest Deposit"
):

    """
    Initiate an M-Pesa STK Push.

    The account should only be credited after
    a successful callback from Safaricom.
    """

    if not MPESA_CONSUMER_KEY:
        return {
            "success": False,
            "message":
                "M-Pesa consumer key is not configured."
        }

    if not MPESA_CONSUMER_SECRET:
        return {
            "success": False,
            "message":
                "M-Pesa consumer secret is not configured."
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

    phone_number = mpesa_phone(phone)

    if not phone_number:
        return {
            "success": False,
            "message":
                "Enter a valid Kenyan M-Pesa number."
        }

    try:

        amount = int(float(amount))

    except Exception:

        return {
            "success": False,
            "message":
                "Invalid M-Pesa amount."
        }

    if amount <= 0:
        return {
            "success": False,
            "message":
                "Amount must be greater than zero."
        }

    token = mpesa_access_token()

    if not token:
        return {
            "success": False,
            "message":
                "Unable to obtain M-Pesa access token."
        }

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d%H%M%S"
    )

    password = mpesa_password(
        timestamp
    )

    payload = {

        "BusinessShortCode":
            MPESA_SHORTCODE,

        "Password":
            password,

        "Timestamp":
            timestamp,

        "TransactionType":
            "CustomerPayBillOnline",

        "Amount":
            amount,

        "PartyA":
            phone_number,

        "PartyB":
            MPESA_SHORTCODE,

        "PhoneNumber":
            phone_number,

        "CallBackURL":
            MPESA_CALLBACK_URL,

        "AccountReference":
            account_reference,

        "TransactionDesc":
            description
    }

    headers = {

        "Authorization":
            f"Bearer {token}",

        "Content-Type":
            "application/json"
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

        if (
            response.ok
            and data.get("ResponseCode") == "0"
        ):

            return {

                "success": True,

                "data": data
            }

        return {

            "success": False,

            "message":
                data.get(
                    "errorMessage",
                    data.get(
                        "ResponseDescription",
                        "M-Pesa request failed."
                    )
                ),

            "data": data
        }

    except requests.exceptions.RequestException as e:

        return {

            "success": False,

            "message":
                f"M-Pesa connection error: {str(e)}"
        }

    except ValueError:

        return {

            "success": False,

            "message":
                "M-Pesa returned an invalid response."
        }

    except Exception as e:

        return {

            "success": False,

            "message":
                f"M-Pesa error: {str(e)}"
        }


# ============================================================
# TEST ROUTE
# ============================================================

@mpesa_bp.route(
    "/mpesa",
    methods=["GET"]
)
def mpesa_status():

    return jsonify({

        "success": True,

        "message":
            "M-Pesa module is working."
    })


# ============================================================
# STK PUSH API ROUTE
# ============================================================

@mpesa_bp.route(
    "/mpesa/stk-push",
    methods=["POST"]
)
def mpesa_stk_push():

    data = request.get_json(
        silent=True
    ) or {}

    phone = data.get(
        "phone"
    )

    amount = data.get(
        "amount"
    )

    account_reference = data.get(
        "account_reference",
        "GlobalVest"
    )

    description = data.get(
        "description",
        "GlobalVest Deposit"
    )

    result = initiate_mpesa_stk(

        phone=phone,

        amount=amount,

        account_reference=
            account_reference,

        description=
            description
    )

    if result.get("success"):

        return jsonify(result), 200

    return jsonify(result), 400


# ============================================================
# M-PESA CALLBACK
# ============================================================

@mpesa_bp.route(
    "/mpesa/callback",
    methods=["POST"]
)
def mpesa_callback():

    data = request.get_json(
        silent=True
    ) or {}

    print(
        "M-Pesa callback received:",
        data
    )

    return jsonify({

        "ResultCode": 0,

        "ResultDesc":
            "Callback received successfully."
    }), 200
