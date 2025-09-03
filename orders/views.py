from django.shortcuts import render, redirect, get_object_or_404
from .models import Order, OrderItem
from cart.cart import Cart  # ✅ Usamos la clase Cart, no más get_cart_items
from django.contrib.auth.decorators import login_required, user_passes_test
from decimal import Decimal
from payments.webpay import crear_transaccion
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.contrib.auth.models import User
from django.db import models
from django.core.paginator import Paginator  # Opcional para paginación
from django.contrib import messages
# ✅ Reutiliza tu Cart
from cart.cart import Cart
from django.http import JsonResponse
import requests



@login_required
def checkout(request):
    cart = Cart(request)
    cart_items = list(cart)

    if not cart_items:
        return redirect('store:product_list')

    total = cart.get_total_price()

    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            total=total,
            status='pending'
        )

        for item in cart_items:
            order_item = OrderItem.objects.create(
                order=order,
                product_id=item['product_id'],
                product_name=item['product'].nombre,
                quantity=item['quantity'],
                subtotal=item['subtotal']
            )

        session_id = str(request.user.id)
        buy_order = f"orden-{order.id}-{get_random_string(6)}"
        return_url = request.build_absolute_uri(reverse('payments:webpay_confirmacion'))

        resultado = crear_transaccion(session_id, total, buy_order, return_url)

        order.token = resultado["token"]
        order.buy_order = buy_order
        order.save()

        request.session['cart'] = {}  # Vaciar carrito tras compra
        request.session.modified = True

        return redirect(f"{resultado['url']}?token_ws={resultado['token']}")

    return render(request, 'orders/checkout.html', {
        'cart_items': cart_items,
        'total': total
    })


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.user != request.user:
        return redirect('store:product_list')

    return render(request, 'orders/order_confirmation.html', {'order': order})


@login_required
def mis_pedidos(request):
    pedidos = Order.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = Paginator(pedidos, 10)  # 10 pedidos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/mis_pedidos.html', {
        'page_obj': page_obj
    })


def is_personal_interno(user):
    return user.groups.filter(name='personal_interno').exists()


@login_required
@user_passes_test(is_personal_interno)
def dashboard_pedidos(request):
    orders = Order.objects.select_related('user').order_by('-created_at')
    return render(request, 'orders/dashboard_pedidos.html', {'orders': orders})


@login_required
@user_passes_test(is_personal_interno)
def detalle_pedido(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()

    if request.method == 'POST' and request.user.groups.filter(name="personal_interno").exists():
        nuevo_estado = request.POST.get("status")
        if nuevo_estado in ['pending', 'paid', 'cancelled']:
            order.status = nuevo_estado
            order.save()
            messages.success(request, "Estado del pedido actualizado correctamente.")

        return redirect('orders:detalle_pedido', order_id=order.id)

    return render(request, 'orders/detalle_pedido.html', {
        'order': order,
        'items': items
    })


def checkout_shipping(request):
    cart = Cart(request)
    cart_items = list(cart)
    total = cart.get_total_price()

    if not cart_items:
        messages.info(request, "Tu carrito está vacío.")
        return redirect("cart:view_cart")

    if request.method == "POST":
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "email": request.POST.get("email"),
            "phone": request.POST.get("phone"),
            "rut": request.POST.get("rut"),
            "address": request.POST.get("address"),
            "address2": request.POST.get("address2"),
            "comuna": request.POST.get("comuna"),
            "region": request.POST.get("region"),
            "notes": request.POST.get("notes"),
            "shipping_method": request.POST.get("shipping_method", "pickup"),
        }
        # Guarda datos temporales de checkout en sesión (o crea Order draft)
        request.session["checkout_shipping"] = data
        return redirect("orders:checkout_pay")

    context = {
        "cart_items": cart_items,
        "total": total,
        # Cárgalas desde tu fuente real; por ahora placeholders
        "comunas": [],
        "regiones": [],
    }
    return render(request, "orders/checkout_datos_envio.html", context)


def checkout_pay(request):
    """
    Paso 3 (Pago): muestra resumen y método de pago.
    Requiere: carrito con items y datos de envío en sesión.
    """
    cart = Cart(request)
    cart_items = list(cart)
    total = cart.get_total_price()
    shipping = request.session.get("checkout_shipping")

    # Si no hay carrito → vuelve al carrito
    if not cart_items:
        messages.error(request, "Tu carrito está vacío.")
        return redirect("cart:view_cart")

    # Si no hay datos de envío → vuelve al paso 2
    if not shipping:
        messages.info(request, "Completa los datos de envío.")
        return redirect("orders:checkout_shipping")

    # GET: renderiza la página de pago (Paso 3)
    return render(request, "orders/checkout_pay.html", {
        "cart_items": cart_items,
        "total": total,
        "shipping": shipping,  # lo usa el template para mostrar resumen
    })

def regiones(request):
    """Devuelve todas las regiones de Chile desde API oficial"""
    url = "https://apis.digital.gob.cl/dpa/regiones"
    res = requests.get(url, timeout=10)
    return JsonResponse(res.json(), safe=False)

def comunas(request, region_code):
    """Devuelve todas las comunas de una región (iterando provincias)"""
    provincias_url = f"https://apis.digital.gob.cl/dpa/regiones/{region_code}/provincias"
    provincias = requests.get(provincias_url, timeout=10).json()

    comunas = []
    for p in provincias:
        comunas_url = f"https://apis.digital.gob.cl/dpa/provincias/{p['codigo']}/comunas"
        comunas.extend(requests.get(comunas_url, timeout=10).json())

    return JsonResponse(comunas, safe=False)