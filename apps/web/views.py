from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseForbidden

from apps.authentication.models import User, FarmerProfile, ProviderProfile, ProviderType
from apps.marketplace.models import ProviderEquipment, WorkCategory, EquipmentImage
from apps.bookings.models import Booking
from apps.bookings.views import calculate_booking_fee

from decimal import Decimal
import random
import logging
import os

logger = logging.getLogger(__name__)

def is_profile_complete(user):
    if not user or not user.is_authenticated:
        return False
    if not user.full_name or user.full_name.strip() == "":
        return False
    if user.role == 'FARMER':
        profile = getattr(user, 'farmer_profile', None)
        if not profile:
            return False
        return bool(profile.village and profile.village.strip() and
                    profile.district and profile.district.strip() and
                    profile.state and profile.state.strip())
    elif user.role == 'PROVIDER':
        profile = getattr(user, 'provider_profile', None)
        if not profile:
            return False
        return bool(profile.village and profile.village.strip() and
                    profile.district and profile.district.strip() and
                    profile.state and profile.state.strip())
    return True


def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'FARMER':
            return redirect('web:farmer_dashboard')
        elif request.user.role == 'PROVIDER':
            return redirect('web:provider_dashboard')
        elif request.user.role == 'ADMIN':
            return redirect('/admin/')
            
    step = 'request_otp'
    mobile = request.POST.get('mobile', '')
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'request_otp':
            if not mobile or len(mobile) < 10:
                messages.error(request, "Please enter a valid 10-digit mobile number.")
            else:
                # Generate and cache OTP
                otp = "123456" if settings.DEBUG else str(random.randint(100000, 999999))
                cache.set(f"otp_{mobile}", otp, timeout=300)
                
                # Output to console/logs for local developer testing
                print(f"---------- WEB OTP for {mobile} is: {otp} ----------")
                logger.info(f"---------- WEB OTP for {mobile} is: {otp} ----------")
                
                messages.success(request, f"OTP sent successfully. For debugging, OTP is {otp}")
                step = 'verify_otp'
                
        elif action == 'verify_otp':
            otp = request.POST.get('otp', '')
            cached_otp = cache.get(f"otp_{mobile}")
            
            # Debug bypass logic
            if not cached_otp and settings.DEBUG and otp == "123456":
                cached_otp = "123456"
                
            if not cached_otp or cached_otp != otp:
                messages.error(request, "Invalid or expired OTP. Please try again.")
                step = 'verify_otp'
            else:
                cache.delete(f"otp_{mobile}")
                # Check user existence
                try:
                    user = User.objects.get(mobile=mobile)
                    if not user.is_verified:
                        user.is_verified = True
                        user.save(update_fields=['is_verified'])
                        
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.full_name}!")
                    
                    if user.role == 'FARMER':
                        return redirect('web:farmer_dashboard')
                    elif user.role == 'PROVIDER':
                        return redirect('web:provider_dashboard')
                    else:
                        return redirect('/admin/')
                except User.DoesNotExist:
                    # Automatically create user with default role 'FARMER' and name as mobile
                    user = User.objects.create_user(
                        mobile=mobile,
                        full_name=mobile,
                        role='FARMER',
                        is_verified=True
                    )
                    # Automatically create farmer profile
                    FarmerProfile.objects.create(
                        user=user,
                        village="",
                        district="",
                        state=""
                    )
                    
                    login(request, user)
                    messages.success(request, "Welcome to KhetSeva! Please complete your profile details.")
                    return redirect('web:farmer_dashboard')
                    
    return render(request, 'web/login.html', {
        'step': step,
        'mobile': mobile,
        'debug_mode': settings.DEBUG
    })

def register_view(request):
    return redirect('web:login')

import math

def haversine_distance(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371.0 # earth radius in km
        return c * r
    except Exception:
        return None

@login_required
def farmer_dashboard(request):
    if request.user.role != 'FARMER':
        return redirect('web:provider_dashboard')
        
    farmer_profile = getattr(request.user, 'farmer_profile', None)
    if not farmer_profile:
        messages.warning(request, "Please complete your farmer profile details first.")
        return redirect('web:profile')
        
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    
    equipments_qs = ProviderEquipment.objects.filter(availability_status=True)
    if search_query:
        equipments_qs = equipments_qs.filter(equipment_name__icontains=search_query) | equipments_qs.filter(description__icontains=search_query)
    if category_id:
        equipments_qs = equipments_qs.filter(category_id=category_id)
        
    # Apply distance filtering & sorting
    lat1 = farmer_profile.latitude
    lon1 = farmer_profile.longitude
    
    equipments = []
    for eq in equipments_qs:
        lat2 = eq.provider.latitude
        lon2 = eq.provider.longitude
        
        if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
            dist = haversine_distance(lat1, lon1, lat2, lon2)
            if dist is not None:
                eq.distance = dist
                # Filter strictly within 20 km range
                if dist <= 20.0:
                    equipments.append(eq)
            else:
                eq.distance = None
                equipments.append(eq)
        else:
            eq.distance = None
            equipments.append(eq)
            
    # Sort equipments: nearest to farthest (None sorted last)
    equipments = sorted(equipments, key=lambda e: (e.distance is None, e.distance or 0.0))
        
    categories = WorkCategory.objects.all()
    bookings = Booking.objects.filter(farmer=request.user).order_by('-booking_date')
    
    profile_complete = is_profile_complete(request.user)
    
    return render(request, 'web/farmer_dashboard.html', {
        'equipments': equipments,
        'categories': categories,
        'bookings': bookings,
        'search_query': search_query,
        'category_id': category_id,
        'farmer_profile': farmer_profile,
        'profile_complete': profile_complete
    })

@login_required
def provider_dashboard(request):
    if request.user.role != 'PROVIDER':
        return redirect('web:farmer_dashboard')
        
    provider_profile = getattr(request.user, 'provider_profile', None)
    if not provider_profile:
        messages.warning(request, "Please complete your provider profile details first.")
        return redirect('web:profile')
        
    equipments = ProviderEquipment.objects.filter(provider=provider_profile)
    categories = WorkCategory.objects.all()
    bookings = Booking.objects.filter(provider=request.user).order_by('-booking_date')
    
    profile_complete = is_profile_complete(request.user)
    
    return render(request, 'web/provider_dashboard.html', {
        'equipments': equipments,
        'categories': categories,
        'bookings': bookings,
        'provider_profile': provider_profile,
        'profile_complete': profile_complete
    })

@login_required
def create_booking(request):
    if request.user.role != 'FARMER':
        return HttpResponseForbidden("Only farmers can book equipment.")
        
    if not is_profile_complete(request.user):
        messages.error(request, "Please complete your profile details first before booking machinery.")
        return redirect('web:profile')
        
    if request.method == 'POST':
        equipment_id = request.POST.get('equipment_id')
        estimated_hours_str = request.POST.get('estimated_hours', '1.0')
        preferred_date = request.POST.get('preferred_date')
        
        equipment = get_object_or_404(ProviderEquipment, pk=equipment_id)
        estimated_hours = Decimal(estimated_hours_str)
        
        if estimated_hours < Decimal('1.0'):
            messages.error(request, "Minimum work duration must be at least 1 hour.")
            return redirect('web:farmer_dashboard')
            
        # Calculate pricing
        total_amount = estimated_hours * equipment.price_per_hour
        booking_fee = calculate_booking_fee(total_amount)
        
        delivery_address_type = request.POST.get('delivery_address_type', 'PROFILE')
        delivery_lat = None
        delivery_lon = None
        
        if delivery_address_type == 'CURRENT':
            curr_lat = request.POST.get('current_latitude')
            curr_lon = request.POST.get('current_longitude')
            if curr_lat and curr_lon:
                try:
                    delivery_lat = Decimal(curr_lat)
                    delivery_lon = Decimal(curr_lon)
                except Exception:
                    pass
                    
        if delivery_lat is None or delivery_lon is None:
            farmer_profile = getattr(request.user, 'farmer_profile', None)
            if farmer_profile:
                delivery_lat = farmer_profile.latitude
                delivery_lon = farmer_profile.longitude
        
        Booking.objects.create(
            farmer=request.user,
            provider=equipment.provider.user,
            equipment=equipment,
            estimated_hours=estimated_hours,
            preferred_date=preferred_date,
            total_amount=total_amount,
            booking_fee=booking_fee,
            booking_status='PENDING',
            delivery_address_type=delivery_address_type,
            delivery_latitude=delivery_lat,
            delivery_longitude=delivery_lon
        )
        messages.success(request, f"Booking request submitted successfully! Waiting for provider approval.")
        
    return redirect('web:farmer_dashboard')

@login_required
def add_equipment(request):
    if request.user.role != 'PROVIDER':
        return HttpResponseForbidden("Only providers can list machinery.")
        
    if not is_profile_complete(request.user):
        messages.error(request, "Please complete your profile details first before listing machinery.")
        return redirect('web:profile')
        
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        name = request.POST.get('equipment_name', '').strip()
        description = request.POST.get('description', '').strip()
        price_per_hour_str = request.POST.get('price_per_hour', '0')
        
        category = get_object_or_404(WorkCategory, pk=category_id)
        price_per_hour = Decimal(price_per_hour_str)
        
        provider_profile = request.user.provider_profile
        
        images = request.FILES.getlist('images')
        
        equipment = ProviderEquipment.objects.create(
            provider=provider_profile,
            category=category,
            equipment_name=name,
            description=description,
            price_per_hour=price_per_hour,
            availability_status=True
        )
        
        for img in images:
            EquipmentImage.objects.create(
                equipment=equipment,
                image=img
            )
            
        # Set primary image from first created gallery image
        primary_eq_img = equipment.images.first()
        if primary_eq_img and primary_eq_img.image:
            equipment.image = primary_eq_img.image
            equipment.save(update_fields=['image'])

        messages.success(request, f"Machinery '{name}' listed successfully!")
        
    return redirect('web:provider_dashboard')

@login_required
def edit_equipment(request, pk):
    equipment = get_object_or_404(ProviderEquipment, pk=pk)
    if equipment.provider.user != request.user:
        return HttpResponseForbidden("Unauthorised action.")
        
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        name = request.POST.get('equipment_name', '').strip()
        description = request.POST.get('description', '').strip()
        price_per_hour_str = request.POST.get('price_per_hour', '0')
        
        category = get_object_or_404(WorkCategory, pk=category_id)
        price_per_hour = Decimal(price_per_hour_str)
        
        equipment.category = category
        equipment.equipment_name = name
        equipment.description = description
        equipment.price_per_hour = price_per_hour
        
        images = request.FILES.getlist('images')
        if images:
            # Overwrite gallery images: delete old files from filesystem & DB
            old_images = equipment.images.all()
            for old_img in old_images:
                if old_img.image and os.path.exists(old_img.image.path):
                    try:
                        os.remove(old_img.image.path)
                    except Exception as e:
                        logger.error(f"Failed to delete old image file: {str(e)}")
            old_images.delete()
            
            # Create new ones first
            for img in images:
                EquipmentImage.objects.create(
                    equipment=equipment,
                    image=img
                )
                
            # Set primary image from first created gallery image
            primary_eq_img = equipment.images.first()
            if primary_eq_img and primary_eq_img.image:
                equipment.image = primary_eq_img.image
                
        equipment.save()
        messages.success(request, f"Machinery '{name}' updated successfully!")
        
    return redirect('web:provider_dashboard')

@login_required
def delete_equipment(request, pk):
    equipment = get_object_or_404(ProviderEquipment, pk=pk)
    if equipment.provider.user != request.user:
        return HttpResponseForbidden("Unauthorised action.")
        
    if request.method == 'POST':
        # Clean up files from storage
        for old_img in equipment.images.all():
            if old_img.image and os.path.exists(old_img.image.path):
                try:
                    os.remove(old_img.image.path)
                except Exception as e:
                    logger.error(f"Failed to delete gallery image: {str(e)}")
        
        name = equipment.equipment_name
        equipment.delete()
        messages.success(request, f"Machinery '{name}' deleted successfully!")
        
    return redirect('web:provider_dashboard')

@login_required
def accept_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.provider != request.user:
        return HttpResponseForbidden("Unauthorised action.")
        
    # Check KYC status
    provider_profile = getattr(request.user, 'provider_profile', None)
    if not provider_profile or provider_profile.verification_status != 'APPROVED':
        messages.error(request, "Your KYC verification is pending approval from admin. You cannot accept bookings yet.")
        return redirect('web:provider_dashboard')
        
    if booking.booking_status == 'PENDING':
        booking.booking_status = 'ACCEPTED'
        booking.save()
        messages.success(request, "Booking accepted! Awaiting farmer payment.")
    else:
        messages.error(request, "Booking cannot be accepted in its current state.")
        
    return redirect('web:provider_dashboard')

@login_required
def reject_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.provider != request.user:
        return HttpResponseForbidden("Unauthorised action.")
        
    if booking.booking_status == 'PENDING':
        booking.booking_status = 'CANCELLED'
        booking.save()
        messages.success(request, "Booking request rejected.")
    else:
        messages.error(request, "Booking cannot be rejected in its current state.")
        
    return redirect('web:provider_dashboard')

@login_required
def pay_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.farmer != request.user:
        return HttpResponseForbidden("Unauthorised action.")
        
    if booking.booking_status == 'ACCEPTED':
        booking.booking_status = 'CONFIRMED'
        booking.payment_id = f"pay_web_simulated_{random.randint(100000, 999999)}"
        booking.save()
        messages.success(request, "Payment successful! Booking confirmed and provider contact details unlocked.")
    else:
        messages.error(request, "Booking is not ready for payment.")
        
    return redirect('web:farmer_dashboard')

@login_required
def start_job(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if booking.provider != request.user:
        return HttpResponseForbidden("Unauthorised action.")
        
    if booking.booking_status == 'CONFIRMED':
        booking.booking_status = 'STARTED'
        booking.save()
        messages.success(request, "Job started! Keep working to complete the task.")
    else:
        messages.error(request, "Job cannot be started in this state.")
        
    return redirect('web:provider_dashboard')

@login_required
def complete_job(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    # Both provider and farmer can trigger job completion for convenience
    if booking.provider != request.user and booking.farmer != request.user:
        return HttpResponseForbidden("Unauthorised action.")
        
    if booking.booking_status in ['CONFIRMED', 'STARTED']:
        booking.booking_status = 'COMPLETED'
        booking.save()
        
        # Award coins to the farmer: 1 coin per ₹100 spent
        farmer = booking.farmer
        coins_earned = int(booking.total_amount // Decimal('100.00'))
        farmer.coins += coins_earned
        farmer.save(update_fields=['coins'])
        
        # Increment jobs completed for provider
        provider_profile = booking.provider.provider_profile
        provider_profile.jobs_completed += 1
        provider_profile.save(update_fields=['jobs_completed'])
        
        messages.success(request, f"Job completed successfully! Farmer earned {coins_earned} loyalty coins.")
    else:
        messages.error(request, "Job cannot be marked completed in this state.")
        
    if request.user.role == 'FARMER':
        return redirect('web:farmer_dashboard')
    else:
        return redirect('web:provider_dashboard')

@login_required
def redeem_coins(request):
    if request.user.role != 'FARMER':
        return HttpResponseForbidden("Only farmers can redeem loyalty coins.")
        
    if request.method == 'POST':
        user = request.user
        if user.coins >= 1000:
            user.coins -= 1000
            user.save(update_fields=['coins'])
            messages.success(request, "Successfully redeemed 1000 loyalty coins for ₹100 cashback voucher code: KHETSEVA100CASHBACK")
        else:
            messages.error(request, "Insufficient coins balance. You need at least 1000 coins.")
            
    return redirect('web:farmer_dashboard')


@login_required
def profile_view(request):
    user = request.user
    
    # Retrieve or create profile objects
    farmer_profile, _ = FarmerProfile.objects.get_or_create(user=user)
    provider_profile, _ = ProviderProfile.objects.get_or_create(user=user)
    provider_types = ProviderType.objects.all()
        
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        village = request.POST.get('village', '').strip()
        district = request.POST.get('district', '').strip()
        state = request.POST.get('state', '').strip()
        custom_village = request.POST.get('custom_village', '').strip()
        if village == 'custom' and custom_village:
            village = custom_village
        
        # Validation checks
        if not full_name or not village or not district or not state:
            messages.error(request, "All fields (Full Name, Village, District, State) are required.")
        else:
            # Check for role update first
            new_role = request.POST.get('role', user.role)
            if new_role in ['FARMER', 'PROVIDER'] and new_role != user.role:
                user.role = new_role
                user.save(update_fields=['role'])
                
                # Copy over address data for smooth switch
                if new_role == 'FARMER':
                    p_prof = getattr(user, 'provider_profile', None)
                    if p_prof and not farmer_profile.village:
                        farmer_profile.village = p_prof.village
                        farmer_profile.district = p_prof.district
                        farmer_profile.state = p_prof.state
                        farmer_profile.latitude = p_prof.latitude
                        farmer_profile.longitude = p_prof.longitude
                        farmer_profile.save()
                elif new_role == 'PROVIDER':
                    f_prof = getattr(user, 'farmer_profile', None)
                    if f_prof and not provider_profile.village:
                        provider_profile.village = f_prof.village
                        provider_profile.district = f_prof.district
                        provider_profile.state = f_prof.state
                        provider_profile.latitude = f_prof.latitude
                        provider_profile.longitude = f_prof.longitude
                        provider_profile.save()
            
            user.full_name = full_name
            
            # Handle profile picture upload
            profile_pic = request.FILES.get('profile_picture')
            if profile_pic:
                user.profile_picture = profile_pic
                
            user.save()
            
            if user.role == 'FARMER':
                farmer_profile.village = village
                farmer_profile.district = district
                farmer_profile.state = state
                
                lat = request.POST.get('latitude')
                lng = request.POST.get('longitude')
                if lat and lng:
                    try:
                        farmer_profile.latitude = Decimal(lat)
                        farmer_profile.longitude = Decimal(lng)
                    except Exception:
                        pass
                farmer_profile.save()
                
            elif user.role == 'PROVIDER':
                provider_profile.village = village
                provider_profile.district = district
                provider_profile.state = state
                
                # Aadhaar & PAN verification documents
                aadhaar = request.POST.get('aadhaar_number', '').strip()
                pan = request.POST.get('pan_number', '').strip()
                doc_file = request.FILES.get('document_file')
                
                provider_profile.aadhaar_number = aadhaar
                provider_profile.pan_number = pan
                if doc_file:
                    provider_profile.document_file = doc_file
                    
                if doc_file or (aadhaar and pan):
                    provider_profile.verification_status = 'PENDING'
                
                provider_type_id = request.POST.get('provider_type_id')
                if provider_type_id:
                    p_type = ProviderType.objects.filter(pk=provider_type_id).first()
                    if p_type:
                        provider_profile.provider_type = p_type
                        
                lat = request.POST.get('latitude')
                lng = request.POST.get('longitude')
                if lat and lng:
                    try:
                        provider_profile.latitude = Decimal(lat)
                        provider_profile.longitude = Decimal(lng)
                    except Exception:
                        pass
                provider_profile.save()
                
            messages.success(request, "Profile details updated successfully!")
            
            if user.role == 'FARMER':
                return redirect('web:farmer_dashboard')
            else:
                return redirect('web:provider_dashboard')
                
    return render(request, 'web/profile.html', {
        'farmer_profile': farmer_profile,
        'provider_profile': provider_profile,
        'provider_types': provider_types,
        'profile_complete': is_profile_complete(user)
    })

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('web:login')

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect

@login_required
def update_location_view(request):
    if request.method == 'POST':
        try:
            lat_str = request.POST.get('latitude')
            lng_str = request.POST.get('longitude')
            if not lat_str or not lng_str:
                return JsonResponse({'status': 'error', 'message': 'Missing coordinates'}, status=400)
                
            lat = Decimal(lat_str)
            lng = Decimal(lng_str)
            
            if request.user.role == 'FARMER':
                profile = getattr(request.user, 'farmer_profile', None)
            else:
                profile = getattr(request.user, 'provider_profile', None)
                
            if profile:
                profile.latitude = lat
                profile.longitude = lng
                profile.save()
                return JsonResponse({'status': 'success', 'message': 'Coordinates updated successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Profile not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)
