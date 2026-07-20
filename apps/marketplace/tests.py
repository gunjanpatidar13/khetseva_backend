from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

from apps.authentication.models import FarmerProfile, ProviderProfile, ProviderType
from apps.marketplace.models import WorkCategory, WorkRequest, Quote
from apps.bookings.models import Booking
from apps.common.anti_bypass import check_anti_bypass_text
from apps.payments.views import calculate_booking_fee

User = get_user_model()


class AntiBypassTestCase(TestCase):
    def test_phone_number_detection(self):
        # Test standard and slightly obfuscated phone numbers
        self.assertTrue(check_anti_bypass_text("Call me at 9876543210"))
        self.assertTrue(check_anti_bypass_text("Contact: +91 98765 43210"))
        self.assertTrue(check_anti_bypass_text("My number is 9 8 7 6 5 4 3 2 1 0"))
        self.assertTrue(check_anti_bypass_text("Nine Eight Seven Six Five Four Three Two One Zero"))

    def test_email_and_social_detection(self):
        # Test emails and links
        self.assertTrue(check_anti_bypass_text("Email me at farm@khetseva.com"))
        self.assertTrue(check_anti_bypass_text("Message me on wa.me/919876543210"))
        self.assertTrue(check_anti_bypass_text("Check my profile on instagram.com/myhandle"))

    def test_clean_messages(self):
        # Test normal messages with no contact info
        self.assertFalse(check_anti_bypass_text("I need 5 acres of wheat harvested tomorrow morning."))
        self.assertFalse(check_anti_bypass_text("Please bring a dual rotavator if possible."))


class BookingFeeTestCase(TestCase):
    def test_booking_fee_caps(self):
        # 5% of quote amount, capped between ₹100 and ₹500
        self.assertEqual(calculate_booking_fee(Decimal('1000.00')), Decimal('100.00')) # 5% is 50 -> capped to 100
        self.assertEqual(calculate_booking_fee(Decimal('5000.00')), Decimal('250.00')) # 5% is 250 -> 250
        self.assertEqual(calculate_booking_fee(Decimal('15000.00')), Decimal('500.00')) # 5% is 750 -> capped to 500


class MarketplaceDistanceTestCase(TestCase):
    def setUp(self):
        # Create categories
        self.category = WorkCategory.objects.create(name="Tilling", description="Tilling work")
        
        # Create users
        self.farmer_user = User.objects.create_user(mobile="1111111111", full_name="Farmer Ramesh", role="FARMER")
        self.provider_user = User.objects.create_user(mobile="2222222222", full_name="Provider Gurpreet", role="PROVIDER")
        
        # Create farmer profile (Navipura coordinates - e.g., Patiala 30.3398, 76.3869)
        FarmerProfile.objects.create(
            user=self.farmer_user,
            village="Navipura",
            district="Patiala",
            state="Punjab",
            latitude=Decimal("30.339800"),
            longitude=Decimal("76.386900")
        )
        
        # Create provider profile (Nearby, ~5km away: 30.3500, 76.4000)
        self.provider_type = ProviderType.objects.create(name="Tractor Owner")
        ProviderProfile.objects.create(
            user=self.provider_user,
            provider_type=self.provider_type,
            village="Navi-East",
            district="Patiala",
            state="Punjab",
            latitude=Decimal("30.350000"),
            longitude=Decimal("76.400000"),
            verification_status="APPROVED"
        )

    def test_distance_query(self):
        # Create a work request at Navipura (30.3398, 76.3869)
        request = WorkRequest.objects.create(
            farmer=self.farmer_user,
            category=self.category,
            title="Need Rotavator work",
            description="5 acres clay soil",
            village="Navipura",
            latitude=Decimal("30.339800"),
            longitude=Decimal("76.386900"),
            acreage=Decimal("5.00"),
            preferred_date="2026-06-16"
        )
        
        # Calculate distance between request and provider (30.3500, 76.4000)
        from django.db.models.functions import Sqrt, Power
        from django.db.models import F
        
        from django.db.models.functions import Cast
        from django.db.models import FloatField
        
        ref_lat = float(self.provider_user.provider_profile.latitude)
        ref_lon = float(self.provider_user.provider_profile.longitude)
        
        annotated_requests = WorkRequest.objects.annotate(
            distance_deg=Sqrt(
                Power(Cast('latitude', FloatField()) - ref_lat, 2) + 
                Power(Cast('longitude', FloatField()) - ref_lon, 2)
            )
        ).annotate(
            distance_km=Cast('distance_deg', FloatField()) * 111.12
        )
        
        self.assertEqual(annotated_requests.count(), 1)
        req = annotated_requests.first()
        
        # Distance should be roughly ~1.8 - 2.2 km
        self.assertLess(req.distance_km, 5.0)
        self.assertGreater(req.distance_km, 1.0)
        print(f"Calculated distance is: {req.distance_km} km")
