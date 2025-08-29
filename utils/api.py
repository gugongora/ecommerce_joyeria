from django.conf import settings
from urllib.parse import urlencode

def build_api_url(endpoint, params=None):
    """
    Construye la URL completa para consumir la API interna, incluyendo parámetros GET si se entregan.
    """
    base_url = settings.API_BASE_URL.rstrip('/') + '/'
    url = f"{base_url}{endpoint.lstrip('/')}"

    if params:
        query_string = urlencode(params)
        url = f"{url}?{query_string}"

    return url
