# tienda_gongora/settings/prod.py
from .base import *  # noqa

DEBUG = False

# Define en .env de prod
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["tu-dominio.cl", "www.tu-dominio.cl"])

# Seguridad
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
REFERRER_POLICY = "same-origin"

# Logging más estricto
LOGGING["root"]["level"] = "WARNING"
LOGGING["loggers"] = {
    "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
}

# Email real (usa variables de entorno)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend"
)