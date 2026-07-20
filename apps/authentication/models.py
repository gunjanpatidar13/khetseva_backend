import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class UserManager(BaseUserManager):
    def create_user(self, mobile, full_name, role, password=None, **extra_fields):
        if not mobile:
            raise ValueError('The Mobile Number field must be set')
        
        # Default status settings
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_verified', False)
        
        user = self.model(
            mobile=mobile,
            full_name=full_name,
            role=role,
            **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(mobile, full_name, role='ADMIN', password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('FARMER', 'Farmer'),
        ('PROVIDER', 'Service Provider'),
        ('ADMIN', 'Admin'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile = models.CharField(max_length=15, unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Required for admin site
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store dynamic devices tokens for Firebase push alerts
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    coins = models.PositiveIntegerField(default=0)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.mobile}) - {self.role}"


class FarmerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='farmer_profile')
    village = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"Farmer Profile: {self.user.full_name}"


class ProviderType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class ProviderProfile(models.Model):
    VERIFICATION_STATUS_CHOICES = (
        ('PENDING', 'Pending Verification'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    provider_type = models.ForeignKey(ProviderType, on_delete=models.SET_NULL, null=True, related_name='providers')
    village = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    jobs_completed = models.PositiveIntegerField(default=0)
    verification_status = models.CharField(
        max_length=15, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='PENDING'
    )
    aadhaar_number = models.CharField(max_length=12, blank=True, default='')
    pan_number = models.CharField(max_length=10, blank=True, default='')
    document_file = models.FileField(upload_to='provider_docs/', blank=True, null=True)

    def __str__(self):
        return f"Provider Profile: {self.user.full_name} ({self.provider_type})"
