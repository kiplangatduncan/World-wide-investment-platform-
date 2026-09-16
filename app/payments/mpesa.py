import base64
import requests

from datetime import datetime

from config import Config


def get_mpesa_base_url():

    if Config.MPESA_ENVIRONMENT.lower() == "production":
        return "https://api.safaricom.co.ke"

    return "https://sandbox.safaricom.co.ke"


def get_access_token():

    url = (
        get_mpesa_base_url()
        + "/oauth/v1/generate"
        + "?grant_type=client_credentials"
    )

    response = requests.get(
        url,
        auth=(
            Config.MPESA_CONSUMER_KEY,
            Config.MPESA_CONSUMER_SECRET
        ),
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data["access_token"]


def initiate_stk_push(
    phone_number,
    amount,
    account_reference
):

    token = get_access_token()

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S"
    )

    password_string = (
        Config.MPESA_SHORTCODE
        + Config.MPESA_PASSKEY
        + timestamp
    )

    password = base64.b64encode(
        password_string.encode()
    ).decode()

    url = (
        get_mpesa_base_url()
        + "/mpesa/stkpush/v1/processrequest"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "BusinessShortCode": Config.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(float(amount)),
        "PartyA": phone_number,
        "PartyB": Config.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": Config.MPESA_CALLBACK_URL,
        "AccountReference": account_reference,
        "TransactionDesc": "Investment Platform Deposit"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()
