# orders/emails.py
from typing import Union, Sequence
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def _send_email(
    to: Union[str, Sequence[str]],
    subject: str,
    template_base: str,
    context: dict,
    from_email: str | None = None,
):
    """
    Envía un correo en texto + HTML usando templates en templates/emails/<template_base>.html/.txt
    """
    if isinstance(to, str):
        to_list = [to]
    else:
        to_list = list(to)

    if not to_list:
        return False

    from_email = from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@localhost")

    txt_body = render_to_string(f"emails/{template_base}.txt", context)
    html_body = render_to_string(f"emails/{template_base}.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=txt_body,
        to=to_list,
        from_email=from_email,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
    return True


def _order_recipient(order) -> str | None:
    """
    Prioriza email del usuario; si no, intenta desde shipping_data si existe.
    """
    user_email = getattr(getattr(order, "user", None), "email", None)
    if user_email:
        return user_email

    shipping_data = getattr(order, "shipping_data", None) or {}
    return shipping_data.get("email")


def send_order_paid_email(order):
    to = _order_recipient(order)
    if not to:
        return False

    ctx = {"order": order}
    _send_email(
        to=to,
        subject=f"¡Gracias! Pedido #{order.id} confirmado",
        template_base="order_paid",
        context=ctx,
    )

    # Notificación a admins si están configurados (settings.ADMINS)
    admin_emails = [email for _, email in getattr(settings, "ADMINS", [])]
    if admin_emails:
        _send_email(
            to=admin_emails,
            subject=f"Nuevo pedido pagado #{order.id}",
            template_base="admin_order_paid",
            context=ctx,
        )
    return True


def send_order_failed_email(order, mensaje: str, detalle: dict | None = None):
    to = _order_recipient(order)
    if not to:
        return False

    ctx = {"order": order, "mensaje": mensaje, "detalle": detalle or {}}
    _send_email(
        to=to,
        subject=f"Tu pago del pedido #{order.id} no se completó",
        template_base="order_failed",
        context=ctx,
    )

    # Notifica a admins
    admin_emails = [email for _, email in getattr(settings, "ADMINS", [])]
    if admin_emails:
        _send_email(
            to=admin_emails,
            subject=f"Pago fallido para pedido #{order.id}",
            template_base="admin_order_failed",
            context=ctx,
        )
    return True
