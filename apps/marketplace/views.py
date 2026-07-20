from django.db.models import Count, F, FloatField
from django.db.models.functions import Sqrt, Power, Cast
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.models import User
from .models import WorkCategory, ProviderEquipment, WorkRequest, Quote, RequestMedia
from .serializers import (
    WorkCategorySerializer,
    ProviderEquipmentSerializer,
    WorkRequestSerializer,
    QuoteSerializer,
    RequestMediaSerializer
)
from .filters import WorkRequestFilter
from .tasks import notify_nearby_providers_task


class IsFarmer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'FARMER'


class IsProvider(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'PROVIDER'


class WorkCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = WorkCategory.objects.all()
    serializer_class = WorkCategorySerializer
    pagination_class = None


class ProviderEquipmentViewSet(viewsets.ModelViewSet):
    serializer_class = ProviderEquipmentSerializer

    def get_queryset(self):
        # Providers manage their own, others can view all
        if self.action in ['update', 'partial_update', 'destroy']:
            return ProviderEquipment.objects.filter(provider__user=self.request.user)
        return ProviderEquipment.objects.all()

    def perform_create(self, serializer):
        profile = self.request.user.provider_profile
        serializer.save(provider=profile)


class WorkRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WorkRequestSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = WorkRequestFilter

    def get_queryset(self):
        user = self.request.user
        
        # Base query annotates count of quotes received
        queryset = WorkRequest.objects.annotate(quotes_count=Count('quotes'))

        # If farmer, retrieve their own requests
        if user.role == 'FARMER':
            return queryset.filter(farmer=user).order_by('-created_at')

        # If provider, retrieve nearby open requests or requests they've quoted on
        elif user.role == 'PROVIDER':
            # Default fallback: return all OPEN requests
            qs = queryset.filter(status__in=['OPEN', 'QUOTED'])
            
            # Spatial filtering based on provider's current coords or profile location
            lat = self.request.query_params.get('latitude')
            lon = self.request.query_params.get('longitude')
            
            ref_lat, ref_lon = None, None
            if lat and lon:
                try:
                    ref_lat = float(lat)
                    ref_lon = float(lon)
                except ValueError:
                    pass
            elif hasattr(user, 'provider_profile') and user.provider_profile.latitude and user.provider_profile.longitude:
                ref_lat = float(user.provider_profile.latitude)
                ref_lon = float(user.provider_profile.longitude)

            if ref_lat is not None and ref_lon is not None:
                # Euclidean distance check (approx 0.18 degrees is ~20km)
                qs = qs.annotate(
                    distance_deg=Sqrt(
                        Power(Cast('latitude', FloatField()) - ref_lat, 2) + 
                        Power(Cast('longitude', FloatField()) - ref_lon, 2)
                    )
                ).filter(
                    distance_deg__lte=0.18
                ).annotate(
                    distance_km=Cast('distance_deg', FloatField()) * 111.12
                ).order_by('distance_deg')
            else:
                qs = qs.order_by('-created_at')
                
            return qs
            
        return queryset.all()

    def perform_create(self, serializer):
        work_request = serializer.save()
        # Trigger Celery background task for nearby providers push alerts
        notify_nearby_providers_task.delay(str(work_request.id))

    @action(detail=True, methods=['post'], permission_classes=[IsFarmer])
    def upload_media(self, request, pk=None):
        work_request = self.get_object()
        # Verify ownership
        if work_request.farmer != request.user:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
            
        files = request.FILES.getlist('files')
        media_type = request.data.get('media_type', 'IMAGE')
        
        uploaded_assets = []
        for f in files:
            asset = RequestMedia.objects.create(
                request=work_request,
                file=f,
                media_type=media_type
            )
            uploaded_assets.append(RequestMediaSerializer(asset).data)
            
        return Response(uploaded_assets, status=status.HTTP_201_CREATED)


class QuoteViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteSerializer

    def get_queryset(self):
        user = self.request.user
        
        # Admin can view all
        if user.is_staff or user.role == 'ADMIN':
            return Quote.objects.all()
            
        # Farmers view quotes submitted for their own work requests
        if user.role == 'FARMER':
            return Quote.objects.filter(request__farmer=user).order_by('-created_at')
            
        # Providers view quotes they have submitted
        elif user.role == 'PROVIDER':
            return Quote.objects.filter(provider=user).order_by('-created_at')
            
        return Quote.objects.none()

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsProvider]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """
        Farmer accepts a quote, transitioning both Quote and WorkRequest statuses.
        A Booking is created subsequently after payment (simulated here).
        """
        quote = self.get_object()
        work_request = quote.request

        # Only the request owner can accept quotes
        if work_request.farmer != request.user:
            return Response({"error": "Only the request owner can accept quotations."}, status=status.HTTP_403_FORBIDDEN)

        if work_request.status in ['BOOKED', 'COMPLETED', 'CANCELLED']:
            return Response({"error": "This request is already finalized or completed."}, status=status.HTTP_400_BAD_REQUEST)

        # Transition statuses
        quote.status = 'ACCEPTED'
        quote.save(update_fields=['status'])
        
        # Reject other quotes
        work_request.quotes.exclude(id=quote.id).update(status='REJECTED')
        
        # We don't mark WorkRequest as BOOKED until payment is confirmed.
        # So we return the quote state. The client is redirected to payments.
        return Response(QuoteSerializer(quote).data, status=status.HTTP_200_OK)
