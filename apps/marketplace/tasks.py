import logging
from celery import shared_task
from django.db.models.functions import Sqrt, Power, Cast
from django.db.models import F, FloatField

from apps.authentication.models import ProviderProfile
from apps.marketplace.models import WorkRequest

logger = logging.getLogger(__name__)


@shared_task
def notify_nearby_providers_task(work_request_id):
    """
    Celery task that performs a coordinates distance check to find all service providers
    within a 20 km radius (~0.18 degrees) of a new work request.
    """
    try:
        work_request = WorkRequest.objects.get(id=work_request_id)
    except WorkRequest.DoesNotExist:
        logger.error(f"WorkRequest with id {work_request_id} does not exist.")
        return False

    lat = float(work_request.latitude)
    lon = float(work_request.longitude)
    category_name = work_request.category.name
    village = work_request.village
    acreage = work_request.acreage

    # Find providers within a 20 km radius (0.18 degrees approx)
    nearby_providers = ProviderProfile.objects.annotate(
        distance_deg=Sqrt(
            Power(Cast('latitude', FloatField()) - lat, 2) + 
            Power(Cast('longitude', FloatField()) - lon, 2)
        )
    ).filter(
        distance_deg__lte=0.18,
        user__is_active=True,
        verification_status='APPROVED' # Ensure we only notify verified service providers
    ).select_related('user')

    tokens = []
    provider_ids = []
    
    for profile in nearby_providers:
        user = profile.user
        if user.fcm_token:
            tokens.append(user.fcm_token)
        provider_ids.append(str(user.id))

    logger.info(f"Found {len(nearby_providers)} providers within 20km for WorkRequest {work_request_id}.")

    # FCM Notification Payload
    title = f"New {category_name} Work Available!"
    body = f"A farmer in {village} needs {acreage} acres worked on. View details and quote now!"
    
    # In production, send notifications to FCM
    # from firebase_admin import messaging
    # if tokens:
    #     message = messaging.MulticastMessage(
    #         notification=messaging.Notification(title=title, body=body),
    #         data={"request_id": str(work_request_id), "type": "NEW_JOB"},
    #         tokens=tokens
    #     )
    #     response = messaging.send_multicast(message)
    #     logger.info(f"FCM Multicast sent: {response.success_count} success, {response.failure_count} failure.")

    # Simulating the notification send in logs
    print(f"--- [NOTIFICATION SIMULATION] ---")
    print(f"To: {len(provider_ids)} providers: {provider_ids}")
    print(f"Tokens: {tokens}")
    print(f"Title: {title}")
    print(f"Body: {body}")
    print(f"---------------------------------")
    
    return True
