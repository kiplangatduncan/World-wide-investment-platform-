import requests

from config import Config


def create_payment(
    amount,
    currency,
    email,
    reference,
    redirect_url=None
):

    url = "https://api.flutterwave.com/v3/payments"

    headers = {
        "Authorization": (
            f"Bearer {Config.FLUTTERWAVE_SECRET_KEY}"
        ),
        "Content-Type": "application/json"
    }

    payload = {
        "tx_ref": reference,
        "amount": amount,
        "currency": currency,
        "redirect_url": (
            redirect_url
            or Config.FLUTTERWAVE_REDIRECT_URL
        ),
        "customer": {
            "email": email
        },
        "customizations": {
            "title": Config.APP_NAME,
            "description": "Investment Platform Deposit"
        }
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()
