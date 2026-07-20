from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.cache import cache
import random

from .models import User, FarmerProfile, ProviderProfile, ProviderType


class ProviderTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderType
        fields = ['id', 'name', 'description']


class FarmerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FarmerProfile
        fields = ['id', 'village', 'district', 'state', 'latitude', 'longitude']


class ProviderProfileSerializer(serializers.ModelSerializer):
    provider_type_details = ProviderTypeSerializer(source='provider_type', read_only=True)
    provider_type = serializers.PrimaryKeyRelatedField(
        queryset=ProviderType.objects.all(), write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = ProviderProfile
        fields = [
            'id', 'provider_type_details', 'provider_type', 'village', 'district', 
            'state', 'latitude', 'longitude', 'rating', 'jobs_completed', 'verification_status'
        ]


class UserSerializer(serializers.ModelSerializer):
    farmer_profile = FarmerProfileSerializer(read_only=True)
    provider_profile = ProviderProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'mobile', 'full_name', 'role', 'is_verified', 'is_active', 'fcm_token', 'farmer_profile', 'provider_profile', 'coins']
        read_only_fields = ['id', 'is_verified', 'is_active', 'coins']


class OTPRequestSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)

    def validate_mobile(self, value):
        # Clean mobile number formats if necessary
        return value


class OTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)


class UserRegisterSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    full_name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=[('FARMER', 'Farmer'), ('PROVIDER', 'Provider')])
    
    # Profile information
    village = serializers.CharField(max_length=100)
    district = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    
    # Provider exclusive details
    provider_type_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_mobile(self, value):
        if User.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("A user with this mobile number already exists.")
        return value

    def create(self, validated_data):
        mobile = validated_data['mobile']
        full_name = validated_data['full_name']
        role = validated_data['role']
        
        lat = validated_data['latitude']
        lon = validated_data['longitude']

        user = User.objects.create_user(
            mobile=mobile,
            full_name=full_name,
            role=role
        )

        if role == 'FARMER':
            FarmerProfile.objects.create(
                user=user,
                village=validated_data['village'],
                district=validated_data['district'],
                state=validated_data['state'],
                latitude=lat,
                longitude=lon
            )
        elif role == 'PROVIDER':
            provider_type = None
            pt_id = validated_data.get('provider_type_id')
            if pt_id:
                try:
                    provider_type = ProviderType.objects.get(id=pt_id)
                except ProviderType.DoesNotExist:
                    pass

            ProviderProfile.objects.create(
                user=user,
                provider_type=provider_type,
                village=validated_data['village'],
                district=validated_data['district'],
                state=validated_data['state'],
                latitude=lat,
                longitude=lon
            )

        return user
