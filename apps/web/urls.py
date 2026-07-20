from django.urls import path
from . import views

app_name = 'web'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('farmer/', views.farmer_dashboard, name='farmer_dashboard'),
    path('provider/', views.provider_dashboard, name='provider_dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Booking lifecycle action routes
    path('booking/<uuid:pk>/accept/', views.accept_booking, name='accept_booking'),
    path('booking/<uuid:pk>/reject/', views.reject_booking, name='reject_booking'),
    path('booking/<uuid:pk>/pay/', views.pay_booking, name='pay_booking'),
    path('booking/<uuid:pk>/start/', views.start_job, name='start_job'),
    path('booking/<uuid:pk>/complete/', views.complete_job, name='complete_job'),
    
    # Equipment actions
    path('equipment/add/', views.add_equipment, name='add_equipment'),
    path('equipment/<uuid:pk>/edit/', views.edit_equipment, name='edit_equipment'),
    path('equipment/<uuid:pk>/delete/', views.delete_equipment, name='delete_equipment'),
    path('booking/create/', views.create_booking, name='create_booking'),
    
    # Redeem coins
    path('redeem/', views.redeem_coins, name='redeem_coins'),
    
    # Location update API
    path('location/update/', views.update_location_view, name='update_location'),
    
    path('logout/', views.logout_view, name='logout'),
]
