from django.conf import settings
import requests, hmac, hashlib


BASE_URL = settings.PAYSTACK_BASE_URL
HEADERS = {
    "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json",
}

def list_banks():
    res = requests.get(f"{BASE_URL}/bank", headers=HEADERS)
    return res.json()

def create_transfer_recipient(name, account_number, bank_code):
    payload = {
        "type": "nuban",
        "name": name,
        "account_number": account_number,
        "bank_code": bank_code,
        "currency": "NGN"
    }
    res = requests.post(f"{BASE_URL}/transferrecipient", json=payload, headers=HEADERS)
    return res.json()

def initialize_transaction(email, amount_kobo, reference, callback_url):
    payload = {
        "email": email,
        "amount": amount_kobo,
        "reference": reference,
        "callback_url": callback_url,
        "channels": ["card", "bank", "ussd", "bank_transfer"],
    }
    res = requests.post(f"{BASE_URL}/transaction/initialize", json=payload, headers=HEADERS)
    return res.json()

def verify_transaction(reference):
    res = requests.get(f"{BASE_URL}/transaction/verify/{reference}", headers=HEADERS)
    return res.json()

def initiate_transfer(amount_kobo, recipient_code, reason, reference):
    payload = {
        "source": "balance",
        "amount": amount_kobo,
        "recipient": recipient_code,
        "reason": reason,
        "reference": reference,
    }
    res = requests.post(f"{BASE_URL}/transfer", json=payload, headers=HEADERS)
    return res.json()

def refund_transaction(transaction_reference, amount_kobo=None):
    payload = {"transaction": transaction_reference}
    if amount_kobo:
        payload["amount"] = amount_kobo
    res = requests.post(f"{BASE_URL}/refund", json=payload, headers=HEADERS)
    return res.json()


# class PaystackError(Exception):
#     pass


# def _headers():
#     return {
#         "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
#         "Content-Type": "application/json",
#     }


# def _post(path, payload):
#     resp = requests.post(f"{BASE_URL}{path}", json=payload, headers=_headers(), timeout=15)
#     data = resp.json()
#     if not data.get("status"):
#         raise PaystackError(data.get("message", "Paystack request failed"))
#     return data["data"]


# def _get(path):
#     resp = requests.get(f"{BASE_URL}{path}", headers=_headers(), timeout=15)
#     data = resp.json()
#     if not data.get("status"):
#         raise PaystackError(data.get("message", "Paystack request failed"))
#     return data["data"]


# def initialize_transaction(*, email: str, amount_kobo: int, reference: str, callback_url: str):
#     return _post("/transaction/initialize", {
#         "email": email,
#         "amount": amount_kobo,
#         "reference": reference,
#         "callback_url": callback_url,
#     })


# def verify_transaction(reference: str):
#     return _get(f"/transaction/verify/{reference}")


# def create_transfer_recipient(*, name: str, account_number: str, bank_code: str):
#     return _post("/transferrecipient", {
#         "type": "nuban",
#         "name": name,
#         "account_number": account_number,
#         "bank_code": bank_code,
#         "currency": "NGN",
#     })


# def initiate_transfer(*, amount_kobo: int, recipient_code: str, reference: str, reason: str):
#     return _post("/transfer", {
#         "source": "balance",
#         "amount": amount_kobo,
#         "recipient": recipient_code,
#         "reference": reference,
#         "reason": reason,
#     })


# def refund_transaction(*, reference: str, amount_kobo: int | None = None):
#     payload = {"transaction": reference}
#     if amount_kobo is not None:
#         payload["amount"] = amount_kobo
#     return _post("/refund", payload)


# def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
#     """
#     Paystack signs the raw request body with HMAC-SHA512 using your
#     secret key. Compare against the x-paystack-signature header.
#     Never trust a webhook payload without this check.
#     """
#     computed = hmac.new(
#         settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
#         raw_body,
#         hashlib.sha512,
#     ).hexdigest()
#     return hmac.compare_digest(computed, signature_header or "")
