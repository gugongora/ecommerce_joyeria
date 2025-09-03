from django.urls import path
from . import views
from .views import dashboard_pedidos
from .views import detalle_pedido
from . import views, api_views   # 👈 importa el nuevo archivo

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('confirmacion/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'), 
    path('dashboard/pedidos/', dashboard_pedidos, name='dashboard_pedidos'),
    path('dashboard/pedidos/<int:order_id>/', detalle_pedido, name='detalle_pedido'),
    path("checkout/shipping/", views.checkout_shipping, name="checkout_shipping"),
    path("checkout/pay/", views.checkout_pay, name="checkout_pay"), 
     # nuevas rutas API
    path("api/regiones/", api_views.regiones, name="api_regiones"),
    path("api/regiones/<str:region_code>/comunas/", api_views.comunas, name="api_comunas"),
]
