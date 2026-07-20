from rest_framework import serializers

from apps.authentication.serializers import UserSerializer
from apps.marketplace.serializers import WorkRequestSerializer, QuoteSerializer, ProviderEquipmentSerializer
from apps.common.anti_bypass import validate_clean_message
from .models import Booking, Review, Complaint


class BookingSerializer(serializers.ModelSerializer):
    request_details = WorkRequestSerializer(source='request', read_only=True)
    quote_details = QuoteSerializer(source='quote', read_only=True)
    equipment_details = ProviderEquipmentSerializer(source='equipment', read_only=True)
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    farmer_mobile = serializers.SerializerMethodField()
    provider_mobile = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'request', 'request_details', 'quote', 'quote_details', 
            'equipment', 'equipment_details', 'farmer', 'farmer_name', 
            'farmer_mobile', 'provider', 'provider_name', 'provider_mobile', 
            'estimated_hours', 'preferred_date', 'total_amount', 'booking_fee', 
            'booking_status', 'booking_date', 'payment_id', 'created_at'
        ]
        read_only_fields = [
            'id', 'farmer', 'provider', 'total_amount', 'booking_fee', 
            'booking_status', 'booking_date', 'payment_id', 'created_at'
        ]

    def get_farmer_mobile(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        current_user = request.user
        
        # Only unlock phone details when booking is confirmed/active
        # and current user is part of the transaction (farmer or provider)
        if obj.booking_status in ['CONFIRMED', 'STARTED', 'COMPLETED']:
            if current_user == obj.farmer or current_user == obj.provider:
                return obj.farmer.mobile
        return None

    def get_provider_mobile(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        current_user = request.user
        
        if obj.booking_status in ['CONFIRMED', 'STARTED', 'COMPLETED']:
            if current_user == obj.farmer or current_user == obj.provider:
                return obj.provider.mobile
        return None


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True)
    reviewee_name = serializers.CharField(source='reviewee.full_name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'booking', 'reviewer', 'reviewer_name', 'reviewee', 'reviewee_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'reviewee', 'created_at']

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_comment(self, value):
        return validate_clean_message(value, "comment")

    def validate(self, attrs):
        booking = attrs.get('booking')
        request_user = self.context['request'].user
        
        # Verify user belongs to booking
        if request_user != booking.farmer and request_user != booking.provider:
            raise serializers.ValidationError("You must be part of this booking to write a review.")
            
        # Verify booking is completed
        if booking.booking_status != 'COMPLETED':
            raise serializers.ValidationError("Reviews can only be written for completed bookings.")
            
        # Verify unique reviewer rule
        if Review.objects.filter(booking=booking, reviewer=request_user).exists():
            raise serializers.ValidationError("You have already reviewed this booking.")
            
        return attrs

    def create(self, validated_data):
        booking = validated_data['booking']
        reviewer = self.context['request'].user
        
        # Assign reviewee automatically
        if reviewer == booking.farmer:
            reviewee = booking.provider
        else:
            reviewee = booking.farmer
            
        validated_data['reviewer'] = reviewer
        validated_data['reviewee'] = reviewee
        
        review = super().create(validated_data)
        
        # Update user profile aggregates
        # We recalculate the average rating and jobs completed for providers
        if reviewee.role == 'PROVIDER':
            profile = reviewee.provider_profile
            reviews = Review.objects.filter(reviewee=reviewee)
            avg_rating = sum(r.rating for r in reviews) / len(reviews)
            profile.rating = avg_rating
            profile.save(update_fields=['rating'])
            
        return review


class ComplaintSerializer(serializers.ModelSerializer):
    raised_by_name = serializers.CharField(source='raised_by.full_name', read_only=True)

    class Meta:
        model = Complaint
        fields = ['id', 'booking', 'raised_by', 'raised_by_name', 'description', 'status', 'created_at']
        read_only_fields = ['id', 'raised_by', 'status', 'created_at']

    def validate(self, attrs):
        booking = attrs.get('booking')
        user = self.context['request'].user
        if user != booking.farmer and user != booking.provider:
            raise serializers.ValidationError("You can only raise complaints for your own bookings.")
        return attrs

    def create(self, validated_data):
        validated_data['raised_by'] = self.context['request'].user
        return super().create(validated_data)
