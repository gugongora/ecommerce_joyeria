# store/urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'store'

urlpatterns = [
    # Rutas más específicas primero
    path('productos/', views.product_list, name='product_list'),
    path('producto/<int:product_id>/', views.product_detail, name='product_detail'),  # 🔧 Modificada
    path('search/', views.search, name='search'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),
    path('dashboard/', views.dashboard_interno, name='dashboard_interno'),
    path('quienes_somos/', views.quienes_somos, name='quienes_somos'),
    path('contacto/', views.contacto, name='contacto'),
    # Ruta base al final
    path('', views.product_list, name='product_list_home'),
    path('catalogo/', views.catalogo_productos, name='catalogo_productos'),
    path('servicios/pedidos-exclusivos/', views.pedidos_exclusivos, name='pedidos_exclusivos'),
    path('servicios/argollas-matrimonio/', views.argollas_matrimonio, name='argollas_matrimonio'),
    path('servicios/argollas-compromiso/', views.argollas_compromiso, name='argollas_compromiso'),
    path('servicios/reparaciones/', views.reparaciones, name='reparaciones'),
    path('servicios/mantenimiento-relojeria/', views.mantenimiento_relojeria, name='mantenimiento_relojeria'),
]
