# payments/views.py
from decimal import Decimal
import logging
import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.crypto import get_random_string

from cart.cart import Cart
from orders.models import Order, OrderItem
from orders.emails import send_order_paid_email, send_order_failed_email

from .webpay import crear_transaccion
from .webpay_conf import (
    WEBPAY_API_BASE_URL,
    WEBPAY_API_KEY_ID,
    WEBPAY_API_KEY_SECRET,
)

logger = logging.getLogger(__name__)

WEBPAY_RESPONSES = {
    0: "Transacción aprobada",
    -1: "Rechazo de la transacción",
    -2: "Transacción debe reintentarse",
    -3: "Error en transacción",
    -4: "Rechazo de transacción",
    -5: "Rechazo por error de tasa",
    -6: "Excede cupo máximo mensual",
    -7: "Excede límite diario por transacción",
    -8: "Rubro no autorizado",
}


@login_required
def webpay_init(request):
    if request.method != "POST":
        return redirect("orders:checkout_pay")

    cart = Cart(request)
    items = list(cart)
    if not items:
        messages.error(request, "Tu carrito está vacío.")
        return redirect("cart:view_cart")

    # Totales
    base_total = cart.get_total_price()  # Decimal
    try:
        shipping_cost = int(request.POST.get("shipping_cost", 0) or 0)
    except (TypeError, ValueError):
        shipping_cost = 0

    amount = int(Decimal(base_total) + Decimal(shipping_cost))  # CLP entero

    # Crea Order solo con campos existentes en tu modelo
    order = Order.objects.create(
        user=request.user,
        total=amount,
        status="pending",
    )

    # Ítems
    for it in items:
        OrderItem.objects.create(
            order=order,
            product_id=it["product_id"],
            product_name=it["product"].nombre,
            quantity=it["quantity"],
            subtotal=it["subtotal"],
        )

    # (Opcional) guardar datos de envío en JSONField si existe
    shipping = request.session.get("checkout_shipping", {})
    if hasattr(order, "shipping_data"):
        order.shipping_data = {**shipping, "shipping_cost": shipping_cost}
        order.save(update_fields=["shipping_data"])

    # Llamada a Webpay (init)
    session_id = str(request.user.id)
    buy_order = f"orden-{order.id}-{get_random_string(6)}"
    return_url = request.build_absolute_uri(reverse("payments:webpay_confirmacion"))

    try:
        resultado = crear_transaccion(session_id, amount, buy_order, return_url)
        # resultado -> {"token": "...", "url": "https://..."}
        order.token = resultado.get("token")
        order.buy_order = buy_order
        order.save(update_fields=["token", "buy_order"])

        # Importante: no vaciamos el carrito aquí; se vacía en confirmación exitosa
        return redirect(f"{resultado['url']}?token_ws={resultado['token']}")

    except Exception as err:
        logger.exception("Fallo en Webpay init: %s", err)
        order.status = "cancelled"
        order.save(update_fields=["status"])

        # Notificar por correo (sin interrumpir el flujo si falla el envío)
        try:
            send_order_failed_email(order, "No se pudo iniciar el pago con Webpay.", {"error": str(err)})
        except Exception as e:
            logger.exception("Error enviando email de init fallido: %s", e)

        return render(request, "orders/payment_result.html", {
            "order": order,
            "estado": "failed",
            "mensaje": "No se pudo iniciar el pago con Webpay.",
            "detalle": {"error": str(err)},
        })


@login_required
def webpay_confirmacion(request):
    token = request.GET.get("token_ws")
    if not token:
        # Cancelado desde Webpay sin token_ws
        return render(request, "orders/payment_result.html", {
            "order": None,
            "estado": "failed",
            "mensaje": "Pago cancelado por el usuario en Webpay.",
            "detalle": {},
        })

    url = f"{WEBPAY_API_BASE_URL}/transactions/{token}"
    headers = {
        "Tbk-Api-Key-Id": WEBPAY_API_KEY_ID,
        "Tbk-Api-Key-Secret": WEBPAY_API_KEY_SECRET,
        "Content-Type": "application/json",
    }

    # Confirmar transacción con Webpay
    try:
        resp = requests.put(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as err:
        logger.exception("Error al confirmar transacción Webpay: %s", err)
        try:
            order = Order.objects.get(token=token)
            order.status = "cancelled"
            order.save(update_fields=["status"])
        except Order.DoesNotExist:
            return HttpResponse("Orden no encontrada para el token", status=404)

        # Email de fallo
        try:
            send_order_failed_email(order, "Error al confirmar el pago con Webpay", {"error": str(err)})
        except Exception as e:
            logger.exception("Error enviando email de error confirmación: %s", e)

        return render(request, "orders/payment_result.html", {
            "order": order,
            "estado": "failed",
            "mensaje": "Error al confirmar el pago con Webpay",
            "detalle": {"error": str(err)},
        })

    try:
        order = Order.objects.get(token=token)
    except Order.DoesNotExist:
        return HttpResponse("Orden no encontrada para el token", status=404)

    status = (data or {}).get("status")

    if status == "AUTHORIZED":
        order.status = "paid"
        order.save(update_fields=["status"])

        # Vaciar carrito
        request.session["cart"] = {}
        request.session.modified = True

        # Email de éxito
        try:
            send_order_paid_email(order)
        except Exception as e:
            logger.exception("Error enviando email de pago exitoso: %s", e)

        return render(request, "orders/payment_result.html", {
            "order": order,
            "estado": "success",
            "mensaje": "Transacción aprobada",
            "detalle": data,
        })

    # Cualquier otro estado => fallo/cancelado
    order.status = "cancelled"
    order.save(update_fields=["status"])
    codigo = (data or {}).get("response_code")
    mensaje = WEBPAY_RESPONSES.get(codigo, "El pago no fue autorizado.")

    try:
        send_order_failed_email(order, mensaje, data)
    except Exception as e:
        logger.exception("Error enviando email de pago fallido: %s", e)

    return render(request, "orders/payment_result.html", {
        "order": order,
        "estado": "failed",
        "mensaje": mensaje,
        "detalle": data,
    })
