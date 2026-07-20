from rest_framework import serializers

from apps.authentication.models import User, ProviderProfile
from apps.authentication.serializers import UserSerializer
from apps.common.anti_bypass import validate_clean_message
from .models import WorkCategory, ProviderEquipment, WorkRequest, RequestMedia, Quote


class WorkCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkCategory
        fields = ['id', 'name', 'description', 'icon']


class ProviderEquipmentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    provider_name = serializers.CharField(source='provider.user.full_name', read_only=True)
    provider_rating = serializers.DecimalField(source='provider.rating', max_digits=3, decimal_places=2, read_only=True)

    class Meta:
        model = ProviderEquipment
        fields = [
            'id', 'provider', 'provider_name', 'provider_rating', 'category', 
            'category_name', 'equipment_name', 'description', 'image', 
            'price_per_hour', 'availability_status'
        ]
        read_only_fields = ['id', 'provider']


class RequestMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestMedia
        fields = ['id', 'file', 'media_type']


# Nested serializer for farmer details, obfuscating contact details
class FarmerPublicSerializer(serializers.ModelSerializer):
    village = serializers.CharField(source='farmer_profile.village', read_only=True)
    district = serializers.CharField(source='farmer_profile.district', read_only=True)
    state = serializers.CharField(source='farmer_profile.state', read_only=True)
    mobile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'mobile', 'village', 'district', 'state']

    def get_mobile(self, obj):
        request = self.context.get('request')
        if not request:
            return None
            
        current_user = request.user
        # Only show mobile number if booking exists and current user is the booked provider
        # Or if the current user is the farmer themselves (obj)
        if current_user.is_anonymous:
            return None
        if current_user == obj:
            return obj.mobile
            
        # Check if there is an active booking between the farmer (obj) and this provider (current_user)
        # We import Booking inside the method to avoid circular imports
        from apps.bookings.models import Booking
        has_confirmed_booking = Booking.objects.filter(
            farmer=obj,
            provider=current_user,
            booking_status='CONFIRMED'
        ).exists()
        
        if has_confirmed_booking:
            return obj.mobile
            
        return None  # Masked before booking


# Nested serializer for provider details, obfuscating contact details
class ProviderPublicSerializer(serializers.ModelSerializer):
    provider_type = serializers.CharField(source='provider_profile.provider_type.name', read_only=True)
    rating = serializers.DecimalField(source='provider_profile.rating', max_digits=3, decimal_places=2, read_only=True)
    jobs_completed = serializers.IntegerField(source='provider_profile.jobs_completed', read_only=True)
    village = serializers.CharField(source='provider_profile.village', read_only=True)
    district = serializers.CharField(source='provider_profile.district', read_only=True)
    state = serializers.CharField(source='provider_profile.state', read_only=True)
    mobile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'mobile', 'provider_type', 'rating', 'jobs_completed', 'village', 'district', 'state']

    def get_mobile(self, obj):
        request = self.context.get('request')
        if not request:
            return None
            
        current_user = request.user
        if current_user.is_anonymous:
            return None
        if current_user == obj:
            return obj.mobile
            
        # Check if there is an active booking between this provider (obj) and the farmer (current_user)
        from apps.bookings.models import Booking
        has_confirmed_booking = Booking.objects.filter(
            farmer=current_user,
            provider=obj,
            booking_status='CONFIRMED'
        ).exists()
        
        if has_confirmed_booking:
            return obj.mobile
            
        return None  # Masked before booking


class WorkRequestSerializer(serializers.ModelSerializer):
    farmer = FarmerPublicSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    media = RequestMediaSerializer(many=True, read_only=True)
    distance = serializers.SerializerMethodField()
    quotes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkRequest
        fields = [
            'id', 'farmer', 'category', 'category_name', 'title', 'description', 
            'village', 'latitude', 'longitude', 'acreage', 'preferred_date', 
            'status', 'created_at', 'media', 'distance', 'quotes_count'
        ]
        read_only_fields = ['id', 'farmer', 'status', 'created_at']

    def get_distance(self, obj):
        # Retrieve computed distance from annotation if available
        if hasattr(obj, 'distance_km') and obj.distance_km is not None:
            return round(float(obj.distance_km), 1)
        return None

    def validate_description(self, value):
        # Scan for PII details (phone numbers, etc.) using anti-bypass rules
        return validate_clean_message(value, "description")

    def create(self, validated_data):
        request = self.context['request']
        validated_data['farmer'] = request.user
        return super().create(validated_data)


class QuoteSerializer(serializers.ModelSerializer):
    provider_details = ProviderPublicSerializer(source='provider', read_only=True)
    request_title = serializers.CharField(source='request.title', read_only=True)
    farmer_id = serializers.UUIDField(source='request.farmer.id', read_only=True)

    class Meta:
        model = Quote
        fields = [
            'id', 'request', 'request_title', 'farmer_id', 'provider', 
            'provider_details', 'amount', 'message', 'estimated_start_date', 
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'provider', 'status', 'created_at']

    def validate_message(self, value):
        # Scan messages for forbidden contact details
        return validate_clean_message(value, "message")

    def validate(self, attrs):
        # Validate that quotes are only sent for OPEN requests
        work_request = attrs.get('request')
        if work_request.status not in ['OPEN', 'QUOTED']:
            raise serializers.ValidationError("Quotes can only be submitted for open work requests.")
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        validated_data['provider'] = request.user
        
        # Transition request status to QUOTED if it was OPEN
        work_request = validated_data['request']
        if work_request.status == 'OPEN':
            work_request.status = 'QUOTED'
            work_request.save(update_fields=['status'])
            
        return super().create(validated_data)
