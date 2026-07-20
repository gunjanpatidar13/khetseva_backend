from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.models import User
from .models import Booking, Review, Complaint
from .serializers import BookingSerializer, ReviewSerializer, ComplaintSerializer


from decimal import Decimal
import random

def calculate_booking_fee(quote_amount):
    fee = quote_amount * Decimal('0.05')
    if fee < Decimal('100.00'):
        return Decimal('100.00')
    if fee > Decimal('500.00'):
        return Decimal('500.00')
    return round(fee, 2)


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return Booking.objects.none()
        if user.role == 'FARMER':
            return Booking.objects.filter(farmer=user).order_by('-booking_date')
        elif user.role == 'PROVIDER':
            return Booking.objects.filter(provider=user).order_by('-booking_date')
        return Booking.objects.all()

    def perform_create(self, serializer):
        user = self.request.user
        equipment = serializer.validated_data.get('equipment')
        estimated_hours = serializer.validated_data.get('estimated_hours', Decimal('1.0'))
        
        # Calculate pricing
        total_amount = estimated_hours * equipment.price_per_hour
        booking_fee = calculate_booking_fee(total_amount)
        
        serializer.save(
            farmer=user,
            provider=equipment.provider.user,
            total_amount=total_amount,
            booking_fee=booking_fee,
            booking_status='PENDING'
        )

    @action(detail=True, methods=['post'])
    def accept_booking(self, request, pk=None):
        booking = self.get_object()
        if booking.provider != request.user:
            return Response({"error": "Only the assigned service provider can accept the booking."}, status=status.HTTP_403_FORBIDDEN)
            
        if booking.booking_status != 'PENDING':
            return Response({"error": "Booking cannot be accepted in this state."}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.booking_status = 'ACCEPTED'
        booking.save(update_fields=['booking_status'])
        return Response(BookingSerializer(booking, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject_booking(self, request, pk=None):
        booking = self.get_object()
        if booking.provider != request.user:
            return Response({"error": "Only the assigned service provider can reject the booking."}, status=status.HTTP_403_FORBIDDEN)
            
        if booking.booking_status != 'PENDING':
            return Response({"error": "Booking cannot be rejected in this state."}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.booking_status = 'CANCELLED'
        booking.save(update_fields=['booking_status'])
        return Response(BookingSerializer(booking, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def pay_booking(self, request, pk=None):
        booking = self.get_object()
        if booking.farmer != request.user:
            return Response({"error": "Only the booking farmer can pay for the booking."}, status=status.HTTP_403_FORBIDDEN)
            
        if booking.booking_status != 'ACCEPTED':
            return Response({"error": "Booking is not in a payable state."}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.booking_status = 'CONFIRMED'
        booking.payment_id = f"pay_mock_{random.randint(100000000, 999999999)}"
        booking.save(update_fields=['booking_status', 'payment_id'])
        
        # If there is a parent request, transition its status
        if booking.request:
            work_request = booking.request
            work_request.status = 'BOOKED'
            work_request.save(update_fields=['status'])
            
        return Response(BookingSerializer(booking, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def start_job(self, request, pk=None):
        booking = self.get_object()
        
        # Only provider can start the job
        if booking.provider != request.user:
            return Response({"error": "Only the assigned service provider can start the job."}, status=status.HTTP_403_FORBIDDEN)
            
        if booking.booking_status != 'CONFIRMED':
            return Response({"error": "Job cannot be started. Booking status must be CONFIRMED."}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.booking_status = 'STARTED'
        booking.save(update_fields=['booking_status'])
        
        # Transition parent request status (optional)
        if booking.request:
            work_request = booking.request
            work_request.status = 'IN_PROGRESS'
            work_request.save(update_fields=['status'])
            
        return Response(BookingSerializer(booking, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete_job(self, request, pk=None):
        booking = self.get_object()
        
        # Both provider and farmer can mark completed
        if request.user != booking.farmer and request.user != booking.provider:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
            
        if booking.booking_status not in ['CONFIRMED', 'STARTED']:
            return Response({"error": "Job cannot be marked complete in this state."}, status=status.HTTP_400_BAD_REQUEST)
            
        booking.booking_status = 'COMPLETED'
        booking.save(update_fields=['booking_status'])
        
        # Transition parent request status (optional)
        if booking.request:
            work_request = booking.request
            work_request.status = 'COMPLETED'
            work_request.save(update_fields=['status'])
            
        # Increment provider's completed jobs counter
        provider_profile = booking.provider.provider_profile
        provider_profile.jobs_completed += 1
        provider_profile.save(update_fields=['jobs_completed'])
        
        # Reward Farmer loyalty coins (1 coin per ₹100 of total amount)
        reward_coins = int(booking.total_amount // Decimal('100.00'))
        if reward_coins > 0:
            farmer = booking.farmer
            farmer.coins += reward_coins
            farmer.save(update_fields=['coins'])
            
        return Response(BookingSerializer(booking, context={'request': request}).data, status=status.HTTP_200_OK)


class ReviewViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        # Allow viewing reviews received by users
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return Review.objects.filter(reviewee_id=user_id).order_by('-created_at')
        return Review.objects.all()

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


class ComplaintViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ComplaintSerializer

    def get_queryset(self):
        user = self.request.user
        return Complaint.objects.filter(raised_by=user).order_by('-created_at')
