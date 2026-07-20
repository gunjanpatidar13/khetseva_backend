import django_filters
from .models import WorkRequest


class WorkRequestFilter(django_filters.FilterSet):
    min_acreage = django_filters.NumberFilter(field_name="acreage", lookup_expr='gte')
    max_acreage = django_filters.NumberFilter(field_name="acreage", lookup_expr='lte')
    start_date = django_filters.DateFilter(field_name="preferred_date", lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name="preferred_date", lookup_expr='lte')

    class Meta:
        model = WorkRequest
        fields = ['category', 'status', 'village', 'preferred_date']
