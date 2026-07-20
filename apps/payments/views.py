from django.conf import settings
from rest_framework import views, permissions, status
from rest_framework.response import Response
from decimal import Decimal

from apps.marketplace.models import Quote, WorkRequest
from apps.bookings.models import Booking
from apps.bookings.serializers import BookingSerializer
from .services import create_razorpay_order, verify_payment_signature


def calculate_booking_fee(quote_amount: Decimal) -> Decimal:
    """
    Calculates the platform booking fee.
    5% of the quotation amount, capped between ₹100 and ₹500.
    """
    fee = quote_amount * Decimal('0.05')
    if fee < Decimal('100.00'):
        return Decimal('100.00')
    if fee > Decimal('500.00'):
        return Decimal('500.00')
    return round(fee, 2)


class CreateOrderView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        quote_id = request.data.get('quote_id')
        if not quote_id:
            return Response({"error": "quote_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            quote = Quote.objects.get(id=quote_id)
        except Quote.DoesNotExist:
            return Response({"error": "Quote not found"}, status=status.HTTP_404_NOT_FOUND)
            
        # Ensure only the request farmer can pay for the booking
        if quote.request.farmer != request.user:
            return Response({"error": "You do not have access to pay for this quote."}, status=status.HTTP_403_FORBIDDEN)
            
        booking_fee = calculate_booking_fee(quote.amount)
        
        # Call Razorpay SDK wrapper
        order = create_razorpay_order(
            amount_in_rupees=float(booking_fee),
            receipt_id=str(quote.id)[:40] # Capped length for Razorpay compliance
        )
        
        return Response({
            "order_id": order.get("id"),
            "amount": float(booking_fee),
            "currency": "INR",
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "quote_id": quote_id
        }, status=status.HTTP_201_CREATED)


class ConfirmPaymentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        quote_id = request.data.get('quote_id')
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')
        
        required_fields = [quote_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]
        if not all(required_fields):
            return Response({"error": "quote_id, razorpay_order_id, razorpay_payment_id, and razorpay_signature are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        # 1. Signature check
        is_valid = verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature
        )
        
        if not is_valid:
            return Response({"error": "Payment verification failed. Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            quote = Quote.objects.select_related('request', 'request__farmer', 'provider').get(id=quote_id)
        except Quote.DoesNotExist:
            return Response({"error": "Quote not found"}, status=status.HTTP_404_NOT_FOUND)
            
        # Ensure only the requesting farmer verifies
        if quote.request.farmer != request.user:
            return Response({"error": "Unauthorized payment verification."}, status=status.HTTP_403_FORBIDDEN)
            
        # Check if booking is already created
        booking, created = Booking.objects.get_or_create(
            request=quote.request,
            quote=quote,
            defaults={
                'farmer': quote.request.farmer,
                'provider': quote.provider,
                'booking_fee': calculate_booking_fee(quote.amount),
                'booking_status': 'CONFIRMED',
                'payment_id': razorpay_payment_id
            }
        )
        
        # 2. Transition request status
        work_request = quote.request
        work_request.status = 'BOOKED'
        work_request.save(update_fields=['status'])
        
        # Update quote status
        quote.status = 'ACCEPTED'
        quote.save(update_fields=['status'])
        
        # Reject other quotes
        work_request.quotes.exclude(id=quote.id).update(status='REJECTED')
        
        # 3. Notify provider about confirmed booking (simulated trigger)
        # In production, dispatch push alert
        print(f"--- [BOOKING SUCCESS CONFIRMED] ---")
        print(f"Provider {quote.provider.full_name} is booked for work: {work_request.title}")
        print(f"Farmer Mobile: {quote.request.farmer.mobile} unlocked.")
        print(f"Provider Mobile: {quote.provider.mobile} unlocked.")
        print(f"-----------------------------------")
        
        serializer = BookingSerializer(booking, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
