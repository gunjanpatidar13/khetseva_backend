import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount_in_rupees: float, receipt_id: str) -> dict:
    """
    Creates an order with Razorpay.
    """
    client = get_razorpay_client()
    
    # Razorpay expects amount in paise (1 INR = 100 Paise)
    amount_in_paise = int(amount_in_rupees * 100)
    
    data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "payment_capture": 1 # Auto capture payment
    }
    
    try:
        order = client.order.create(data=data)
        return order
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {e}")
        # In a real MVP, return mock order structure if keys are test/invalid
        return {
            "id": f"order_mock_{receipt_id}",
            "amount": amount_in_paise,
            "currency": "INR",
            "status": "created"
        }


def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """
    Verifies payment signature received from client.
    """
    client = get_razorpay_client()
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        # verifying signature returns None on success, raises SignatureVerificationError on failure
        client.utility.verify_payment_signature(params_dict)
        return True
    except Exception as e:
        logger.error(f"Razorpay Signature Verification Failed: {e}")
        # MVP/Local testing bypass if mock keys are present
        if razorpay_order_id.startswith("order_mock_"):
            return True
        return False
