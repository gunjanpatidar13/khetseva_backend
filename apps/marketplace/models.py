import uuid
from django.db import models
from django.conf import settings


class WorkCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='categories/icons/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Work Categories"

    def __str__(self):
        return self.name


class ProviderEquipment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Reference ProviderProfile
    provider = models.ForeignKey(
        'authentication.ProviderProfile', 
        on_delete=models.CASCADE, 
        related_name='equipments'
    )
    category = models.ForeignKey(WorkCategory, on_delete=models.PROTECT, related_name='equipments')
    equipment_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='provider_equipments/', blank=True, null=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    availability_status = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.equipment_name} - {self.provider.user.full_name}"


class WorkRequest(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('OPEN', 'Open for Bids'),
        ('QUOTED', 'Quoted'),
        ('BOOKED', 'Booked / Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='work_requests',
        limit_choices_to={'role': 'FARMER'}
    )
    category = models.ForeignKey(WorkCategory, on_delete=models.PROTECT, related_name='work_requests')
    title = models.CharField(max_length=200)
    description = models.TextField()
    village = models.CharField(max_length=100)
    
    # Coordinates stored as standard decimal values
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    acreage = models.DecimalField(max_digits=6, decimal_places=2)
    preferred_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.village}) - {self.status}"


class RequestMedia(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(WorkRequest, on_delete=models.CASCADE, related_name='media')
    file = models.FileField(upload_to='work_requests/media/')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='IMAGE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Media for Request: {self.request.id} ({self.media_type})"


class Quote(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending decision'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(WorkRequest, on_delete=models.CASCADE, related_name='quotes')
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='quotes',
        limit_choices_to={'role': 'PROVIDER'}
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField()
    estimated_start_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quote from {self.provider.full_name} for {self.request.title} - ₹{self.amount}"


class EquipmentImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment = models.ForeignKey(
        ProviderEquipment, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(upload_to='provider_equipments/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.equipment.equipment_name}"

