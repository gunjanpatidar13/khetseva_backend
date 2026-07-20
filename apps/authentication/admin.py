from django.contrib import admin
from .models import User, FarmerProfile, ProviderProfile, ProviderType

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('mobile', 'full_name', 'role', 'is_verified', 'is_active')
    search_fields = ('mobile', 'full_name')
    list_filter = ('role', 'is_verified', 'is_active')

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'village', 'district', 'state', 'latitude', 'longitude')
    search_fields = ('user__full_name', 'village')

@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider_type', 'village', 'rating', 'jobs_completed')
    list_filter = ('provider_type',)
    search_fields = ('user__full_name', 'village')

@admin.register(ProviderType)
class ProviderTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
