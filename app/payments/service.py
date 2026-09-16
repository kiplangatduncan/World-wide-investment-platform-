from app.payments.mpesa import initiate_stk_push
from app.payments.flutterwave import create_payment


SUPPORTED_PAYMENT_METHODS = {

    "Kenya": {
        "currency": "KES",
        "methods": [
            "M-Pesa",
            "Card"
        ]
    },

    "Uganda": {
        "currency": "UGX",
        "methods": [
            "MTN Mobile Money",
            "Airtel Money",
            "Card"
        ]
    },

    "Tanzania": {
        "currency": "TZS",
        "methods": [
            "Airtel Money",
            "Tigo Pesa",
            "HaloPesa",
            "Vodacom",
            "Card"
        ]
    },

    "Rwanda": {
        "currency": "RWF",
        "methods": [
            "MTN Mobile Money",
            "Airtel Money",
            "Card"
        ]
    },

    "Nigeria": {
        "currency": "NGN",
        "methods": [
            "Card",
            "Bank Transfer",
            "USSD"
        ]
    },

    "South Africa": {
        "currency": "ZAR",
        "methods": [
            "Card",
            "Bank",
            "EFT"
        ]
    },

    "United Kingdom": {
        "currency": "GBP",
        "methods": [
            "Card",
            "Apple Pay"
        ]
    },

    "United States": {
        "currency": "USD",
        "methods": [
            "Card",
            "Apple Pay"
        ]
    },

    "Europe": {
        "currency": "EUR",
        "methods": [
            "Card",
            "Apple Pay"
        ]
    }
}


def get_country_payment_methods(country):

    return SUPPORTED_PAYMENT_METHODS.get(
        country,
        {
            "currency": "USD",
            "methods": ["Card"]
        }
    )


def start_mpesa_payment(
    phone_number,
    amount,
    reference
):

    return initiate_stk_push(
        phone_number=phone_number,
        amount=amount,
        account_reference=reference
    )


def start_card_payment(
    amount,
    currency,
    email,
    reference,
    redirect_url=None
):

    return create_payment(
        amount=amount,
        currency=currency,
        email=email,
        reference=reference,
        redirect_url=redirect_url
    )
