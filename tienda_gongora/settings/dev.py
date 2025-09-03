# tienda_gongora/settings/dev.py
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


DATABASES = {
    'default': {
       'ENGINE': 'django.db.backends.mysql',
        'NAME': 'tiendagongora',
        'USER': 'root',
        'PASSWORD': 'eldiablo1',  # pon tu contraseña si es que tienes
        'HOST': '127.0.0.1',
       'PORT': '3306',
   }
}


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"