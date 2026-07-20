import random
import logging
from django.core.cache import cache
from django.conf import settings
from rest_framework import status, views, permissions, generics
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import UserRateThrottle

from .models import User, ProviderType
from .serializers import (
    OTPRequestSerializer,
    OTPVerifySerializer,
    UserRegisterSerializer,
    UserSerializer,
    ProviderTypeSerializer
)

logger = logging.getLogger(__name__)


class OTPThrottle(UserRateThrottle):
    scope = 'otp_request'


class RequestOTPView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request, *args, **kwargs):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data['mobile']
        
        # In a real app, integrate an SMS gateway here (e.g. Msg91 / Twilio)
        # Generate 6-digit numeric OTP
        otp = "123456" if settings.DEBUG else str(random.randint(100000, 999999))
        
        # Save OTP to cache for 5 minutes (300 seconds)
        cache.set(f"otp_{mobile}", otp, timeout=300)
        
        # Print to terminal for debugging and local testing
        logger.info(f"---------- OTP for {mobile} is: {otp} ----------")
        print(f"---------- OTP for {mobile} is: {otp} ----------")
        
        response_data = {"message": "OTP sent successfully."}
        if settings.DEBUG:
            response_data["debug_otp"] = otp  # Return OTP in debug mode for easier mobile development
            
        return Response(response_data, status=status.HTTP_200_OK)


class VerifyOTPView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mobile = serializer.validated_data['mobile']
        otp = serializer.validated_data['otp']
        
        cached_otp = cache.get(f"otp_{mobile}")
        
        # Developer/MVP convenience bypass check
        if not cached_otp and settings.DEBUG and otp == "123456":
            cached_otp = "123456"

        if not cached_otp or cached_otp != otp:
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        
        # OTP is verified, remove it from cache
        cache.delete(f"otp_{mobile}")
        
        # Check if user already exists
        try:
            user = User.objects.get(mobile=mobile)
            # Mark verified
            if not user.is_verified:
                user.is_verified = True
                user.save(update_fields=['is_verified'])
                
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "registered": True,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            # Save verification token to allow registration
            reg_token = str(random.randint(100000, 999999))
            cache.set(f"reg_verified_{mobile}", reg_token, timeout=600) # Valid for 10 minutes
            
            return Response({
                "registered": False,
                "mobile": mobile,
                "registration_token": reg_token,
                "message": "Mobile verified. Please complete your registration."
            }, status=status.HTTP_200_OK)


class RegisterView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mobile = serializer.validated_data['mobile']
        
        # Secure registration token validation
        # Skip token check if in DEBUG mode for developer ease
        if not settings.DEBUG:
            reg_token = request.data.get('registration_token')
            cached_token = cache.get(f"reg_verified_{mobile}")
            if not cached_token or cached_token != reg_token:
                return Response({"error": "OTP verification is required before registration."}, status=status.HTTP_400_BAD_REQUEST)
            cache.delete(f"reg_verified_{mobile}")

        user = serializer.save()
        user.is_verified = True
        user.save(update_fields=['is_verified'])
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ProviderTypeListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    queryset = ProviderType.objects.all()
    serializer_class = ProviderTypeSerializer
    pagination_class = None


class RedeemCoinsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.coins >= 1000:
            user.coins -= 1000
            user.save(update_fields=['coins'])
            return Response({
                "message": "Successfully redeemed 1000 coins! ₹100 cashback voucher added to your account.",
                "coins": user.coins
            }, status=status.HTTP_200_OK)
        return Response({
            "error": f"Insufficient coins. You have {user.coins} coins, but need at least 1000 to redeem."
        }, status=status.HTTP_400_BAD_REQUEST)
