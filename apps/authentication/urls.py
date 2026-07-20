from django.urls import path
from .views import (
    RequestOTPView,
    VerifyOTPView,
    RegisterView,
    UserProfileView,
    ProviderTypeListView,
    RedeemCoinsView
)

urlpatterns = [
    path('otp/request/', RequestOTPView.as_view(), name='otp-request'),
    path('otp/verify/', VerifyOTPView.as_view(), name='otp-verify'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('redeem/', RedeemCoinsView.as_view(), name='redeem-coins'),
    path('provider-types/', ProviderTypeListView.as_view(), name='provider-types'),
]
