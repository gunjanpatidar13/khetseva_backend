import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'khetseva.settings')
django.setup()

from apps.authentication.models import User, FarmerProfile, ProviderProfile, ProviderType
from apps.marketplace.models import WorkCategory, ProviderEquipment, WorkRequest, EquipmentImage
from apps.bookings.models import Booking

def seed():
    # 1. Seed Provider Types
    pt_tractor, _ = ProviderType.objects.get_or_create(
        name="Tractor Owner",
        defaults={"description": "Providers owning utility tractors for tilling, ploughing, and haulage."}
    )
    pt_harvester, _ = ProviderType.objects.get_or_create(
        name="Harvester Operator",
        defaults={"description": "Operators with combine harvesters for wheat, paddy, and sugarcane."}
    )
    pt_borewell, _ = ProviderType.objects.get_or_create(
        name="Borewell Contractor",
        defaults={"description": "Contractors specialized in deep tilling and borewell drilling."}
    )

    # 2. Seed Farmers
    # Farmer 1
    f1_user, created = User.objects.get_or_create(
        mobile="9876543210",
        defaults={"full_name": "Ramesh Kumar", "role": "FARMER", "is_verified": True}
    )
    if created:
        f1_user.set_password("khetseva123")
        f1_user.save()
    FarmerProfile.objects.get_or_create(
        user=f1_user,
        defaults={
            "village": "Navipura",
            "district": "Patiala",
            "state": "Punjab",
            "latitude": 30.3398,
            "longitude": 76.3869
        }
    )

    # Farmer 2
    f2_user, created = User.objects.get_or_create(
        mobile="9111111111",
        defaults={"full_name": "Suresh Singh", "role": "FARMER", "is_verified": True}
    )
    if created:
        f2_user.set_password("khetseva123")
        f2_user.save()
    FarmerProfile.objects.get_or_create(
        user=f2_user,
        defaults={
            "village": "Rampur",
            "district": "Patiala",
            "state": "Punjab",
            "latitude": 30.3550,
            "longitude": 76.4010
        }
    )

    # 3. Seed Service Providers
    # Provider 1 (Gurpreet Singh)
    p1_user, created = User.objects.get_or_create(
        mobile="8888888888",
        defaults={"full_name": "Gurpreet Singh", "role": "PROVIDER", "is_verified": True}
    )
    if created:
        p1_user.set_password("khetseva123")
        p1_user.save()
    p1_profile, _ = ProviderProfile.objects.get_or_create(
        user=p1_user,
        defaults={
            "provider_type": pt_tractor,
            "village": "Navipura",
            "district": "Patiala",
            "state": "Punjab",
            "latitude": 30.3398,
            "longitude": 76.3869,
            "jobs_completed": 5,
            "rating": 4.8
        }
    )

    # Provider 2 (Harbhajan Singh)
    p2_user, created = User.objects.get_or_create(
        mobile="8222222222",
        defaults={"full_name": "Harbhajan Singh", "role": "PROVIDER", "is_verified": True}
    )
    if created:
        p2_user.set_password("khetseva123")
        p2_user.save()
    p2_profile, _ = ProviderProfile.objects.get_or_create(
        user=p2_user,
        defaults={
            "provider_type": pt_harvester,
            "village": "Navipura",
            "district": "Patiala",
            "state": "Punjab",
            "latitude": 30.3420,
            "longitude": 76.3900,
            "jobs_completed": 12,
            "rating": 4.9
        }
    )

    # 4. Seed Provider Equipment
    cat_rotavator, _ = WorkCategory.objects.get_or_create(
        name="Rotavator Work",
        defaults={"description": "Tilling and soil preparation using rotavator machinery."}
    )
    cat_harvesting, _ = WorkCategory.objects.get_or_create(
        name="Harvesting",
        defaults={"description": "Harvester services for harvesting paddy, wheat, and sugarcane."}
    )
    cat_cultivation, _ = WorkCategory.objects.get_or_create(
        name="Cultivation",
        defaults={"description": "Ploughing and cultivation services."}
    )
    cat_borewell, _ = WorkCategory.objects.get_or_create(
        name="Borewell Drilling",
        defaults={"description": "Drilling and boring services."}
    )
    cat_baling, _ = WorkCategory.objects.get_or_create(
        name="Bailing",
        defaults={"description": "Straw baler services for compressing hay and residue."}
    )
    cat_haulage, _ = WorkCategory.objects.get_or_create(
        name="Haulage & Transport",
        defaults={"description": "Tractor trolleys for agricultural transport."}
    )
    cat_sowing, _ = WorkCategory.objects.get_or_create(
        name="Sowing & Planting",
        defaults={"description": "Seed drills and automatic planting services."}
    )
    cat_spraying, _ = WorkCategory.objects.get_or_create(
        name="Pest Control",
        defaults={"description": "Boom sprayers for pesticide/fertilizer treatment."}
    )

    eq1, created = ProviderEquipment.objects.get_or_create(
        provider=p1_profile,
        category=cat_rotavator,
        defaults={
            "equipment_name": "John Deere 5050D Tractor + Rotavator",
            "description": "50 HP tractor equipped with 7 feet heavy tilling rotavator.",
            "price_per_hour": 800.00,
            "image": "provider_equipments/rotavator.png",
            "availability_status": True
        }
    )
    if created or eq1.image == "":
        eq1.image = "provider_equipments/rotavator.png"
        eq1.save()
    EquipmentImage.objects.get_or_create(
        equipment=eq1,
        image="provider_equipments/rotavator.png"
    )

    eq2, created = ProviderEquipment.objects.get_or_create(
        provider=p2_profile,
        category=cat_harvesting,
        defaults={
            "equipment_name": "Class Crop Tiger 30 Harvester",
            "description": "Compact track combine harvester, ideal for muddy fields.",
            "price_per_hour": 2500.00,
            "image": "provider_equipments/harvester.png",
            "availability_status": True
        }
    )
    if created or eq2.image == "":
        eq2.image = "provider_equipments/harvester.png"
        eq2.save()
    EquipmentImage.objects.get_or_create(
        equipment=eq2,
        image="provider_equipments/harvester.png"
    )

    eq3, created = ProviderEquipment.objects.get_or_create(
        provider=p1_profile,
        category=cat_borewell,
        defaults={
            "equipment_name": "Ashok Leyland Borewell Rig Truck",
            "description": "Heavy-duty truck-mounted rig capable of drilling up to 600 feet.",
            "price_per_hour": 1800.00,
            "image": "provider_equipments/borewell.png",
            "availability_status": True
        }
    )
    if created or eq3.image == "":
        eq3.image = "provider_equipments/borewell.png"
        eq3.save()
    EquipmentImage.objects.get_or_create(
        equipment=eq3,
        image="provider_equipments/borewell.png"
    )

    # 5. Seed an Open Work Request by Ramesh Kumar (so providers can see it instantly)
    WorkRequest.objects.get_or_create(
        farmer=f1_user,
        category=cat_rotavator,
        defaults={
            "title": "Tilling 4 Acres Clay Soil",
            "description": "Need rotavator tilling for 4 acres of heavy soil. Preferred start date tomorrow morning.",
            "village": "Navipura",
            "latitude": 30.3398,
            "longitude": 76.3869,
            "acreage": 4.0,
            "preferred_date": "2026-06-16",
            "status": "OPEN"
        }
    )

    # 6. Seed Bookings in various states
    # Pending approval booking
    Booking.objects.get_or_create(
        farmer=f1_user,
        provider=p1_user,
        equipment=eq1,
        booking_status='PENDING',
        defaults={
            "estimated_hours": 4.00,
            "preferred_date": "2026-07-20",
            "total_amount": 3200.00,
            "booking_fee": 160.00
        }
    )

    # Accepted (Unpaid) booking
    Booking.objects.get_or_create(
        farmer=f1_user,
        provider=p2_user,
        equipment=eq2,
        booking_status='ACCEPTED',
        defaults={
            "estimated_hours": 8.00,
            "preferred_date": "2026-07-21",
            "total_amount": 20000.00,
            "booking_fee": 500.00
        }
    )

    # Confirmed (Paid) booking
    Booking.objects.get_or_create(
        farmer=f1_user,
        provider=p1_user,
        equipment=eq3,
        booking_status='CONFIRMED',
        defaults={
            "estimated_hours": 5.00,
            "preferred_date": "2026-07-19",
            "total_amount": 9000.00,
            "booking_fee": 450.00
        }
    )

    # In progress (Started) booking
    Booking.objects.get_or_create(
        farmer=f1_user,
        provider=p1_user,
        equipment=eq1,
        booking_status='STARTED',
        defaults={
            "estimated_hours": 3.00,
            "preferred_date": "2026-07-18",
            "total_amount": 2400.00,
            "booking_fee": 120.00
        }
    )

    # Completed booking
    Booking.objects.get_or_create(
        farmer=f1_user,
        provider=p2_user,
        equipment=eq2,
        booking_status='COMPLETED',
        defaults={
            "estimated_hours": 6.00,
            "preferred_date": "2026-07-17",
            "total_amount": 15000.00,
            "booking_fee": 500.00
        }
    )

    print("Data seeded successfully!")

if __name__ == "__main__":
    seed()
