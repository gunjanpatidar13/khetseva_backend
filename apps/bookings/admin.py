from django.contrib import admin
from .models import Booking, Review, Complaint

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('request', 'quote', 'farmer', 'provider', 'booking_fee', 'booking_status', 'booking_date')
    list_filter = ('booking_status',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'reviewee', 'rating', 'comment', 'created_at')

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('booking', 'raised_by', 'status', 'created_at')
    list_filter = ('status',)
