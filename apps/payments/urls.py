from django.urls import path
from .views import CreateOrderView, ConfirmPaymentView

urlpatterns = [
    path('create-order/', CreateOrderView.as_view(), name='create-order'),
    path('confirm-payment/', ConfirmPaymentView.as_view(), name='confirm-payment'),
]
