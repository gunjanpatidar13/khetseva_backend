from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkCategoryViewSet,
    ProviderEquipmentViewSet,
    WorkRequestViewSet,
    QuoteViewSet
)

router = DefaultRouter()
router.register(r'categories', WorkCategoryViewSet, basename='category')
router.register(r'equipment', ProviderEquipmentViewSet, basename='equipment')
router.register(r'requests', WorkRequestViewSet, basename='request')
router.register(r'quotes', QuoteViewSet, basename='quote')

urlpatterns = [
    path('', include(router.urls)),
]
