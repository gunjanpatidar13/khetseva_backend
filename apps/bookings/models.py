import uuid
from django.db import models
from django.conf import settings


class Booking(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('ACCEPTED', 'Accepted (Unpaid)'),
        ('CONFIRMED', 'Confirmed (Paid)'),
        ('STARTED', 'Job Started'),
        ('COMPLETED', 'Job Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(
        'marketplace.WorkRequest', 
        on_delete=models.SET_NULL, 
        related_name='booking',
        null=True,
        blank=True
    )
    quote = models.OneToOneField(
        'marketplace.Quote', 
        on_delete=models.SET_NULL, 
        related_name='booking',
        null=True,
        blank=True
    )
    equipment = models.ForeignKey(
        'marketplace.ProviderEquipment',
        on_delete=models.SET_NULL,
        related_name='bookings',
        null=True,
        blank=True
    )
    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='bookings_as_farmer',
        limit_choices_to={'role': 'FARMER'}
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='bookings_as_provider',
        limit_choices_to={'role': 'PROVIDER'}
    )
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    preferred_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    booking_fee = models.DecimalField(max_digits=8, decimal_places=2)
    booking_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    booking_date = models.DateTimeField(auto_now_add=True)
    
    # Target delivery address/GPS coordinates for this booking
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_address_type = models.CharField(max_length=20, default='PROFILE')
    
    # Store payment gateway reference (e.g. Razorpay payment ID / order ID)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        title = self.request.title if self.request else (self.equipment.equipment_name if self.equipment else "Booking")
        return f"Booking: {title} - {self.booking_status}"

    @property
    def farmer_name(self):
        return self.farmer.full_name if self.farmer else ""

    @property
    def farmer_mobile(self):
        return self.farmer.mobile if self.farmer else ""

    @property
    def provider_mobile(self):
        return self.provider.mobile if self.provider else ""

    @property
    def final_latitude(self):
        if self.delivery_latitude is not None:
            return self.delivery_latitude
        if self.farmer and hasattr(self.farmer, 'farmer_profile'):
            return self.farmer.farmer_profile.latitude
        return None

    @property
    def final_longitude(self):
        if self.delivery_longitude is not None:
            return self.delivery_longitude
        if self.farmer and hasattr(self.farmer, 'farmer_profile'):
            return self.farmer.farmer_profile.longitude
        return None


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='reviews_written'
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='reviews_received'
    )
    rating = models.PositiveSmallIntegerField() # 1 to 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'reviewer') # Can only review once per booking

    def __str__(self):
        return f"Review by {self.reviewer.full_name} for {self.reviewee.full_name}: {self.rating} stars"


class Complaint(models.Model):
    STATUS_CHOICES = (
        ('OPEN', 'Open'),
        ('INVESTIGATING', 'Under Investigation'),
        ('RESOLVED', 'Resolved'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='complaints')
    raised_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='complaints_raised')
    description = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint on {self.booking.id} - Status: {self.status}"
