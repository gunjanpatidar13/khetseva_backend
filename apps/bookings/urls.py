from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, ReviewViewSet, ComplaintViewSet

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'complaints', ComplaintViewSet, basename='complaint')

urlpatterns = [
    path('', include(router.urls)),
]
