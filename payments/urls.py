from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path("webpay/init/", views.webpay_init, name="webpay_init"),
    path("webpay/confirmacion/", views.webpay_confirmacion, name="webpay_confirmacion"),
]