from django.contrib import admin
from .models import WorkCategory, ProviderEquipment, WorkRequest, Quote, RequestMedia

@admin.register(WorkCategory)
class WorkCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(ProviderEquipment)
class ProviderEquipmentAdmin(admin.ModelAdmin):
    list_display = ('equipment_name', 'provider', 'category', 'availability_status')
    list_filter = ('category', 'availability_status')

@admin.register(WorkRequest)
class WorkRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'farmer', 'category', 'village', 'acreage', 'preferred_date', 'status')
    list_filter = ('status', 'category')
    search_fields = ('title', 'village')

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('request', 'provider', 'amount', 'estimated_start_date', 'status')
    list_filter = ('status',)

admin.site.register(RequestMedia)
