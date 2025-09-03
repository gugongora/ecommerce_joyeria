# orders/api_views.py
import json
import time
from pathlib import Path

import requests
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseServerError

# === Config API externa ===
DPA_BASE = "https://apis.digital.gob.cl/dpa"
HEADERS = {"User-Agent": "GongoraStore/1.0", "Accept": "application/json"}
TIMEOUT = 8
RETRIES = 2
CACHE_TTL = 60 * 60 * 24 * 7  # 7 días

# === Rutas a fallbacks locales (opcionales) ===
BASE_DIR = Path(__file__).resolve().parent
FALLBACK_DIR = BASE_DIR / "data"
FALLBACK_REGIONES = FALLBACK_DIR / "regiones.json"
FALLBACK_COMUNAS_BY_REGION = FALLBACK_DIR / "comunas_by_region.json"

# === Fallback embebido (por si no existen archivos) ===
EMBED_REGIONES = [
    {"codigo": "01", "nombre": "Región de Tarapacá"},
    {"codigo": "02", "nombre": "Región de Antofagasta"},
    {"codigo": "03", "nombre": "Región de Atacama"},
    {"codigo": "04", "nombre": "Región de Coquimbo"},
    {"codigo": "05", "nombre": "Región de Valparaíso"},
    {"codigo": "06", "nombre": "Región del Libertador General Bernardo O'Higgins"},
    {"codigo": "07", "nombre": "Región del Maule"},
    {"codigo": "08", "nombre": "Región del Biobío"},
    {"codigo": "09", "nombre": "Región de La Araucanía"},
    {"codigo": "10", "nombre": "Región de Los Lagos"},
    {"codigo": "11", "nombre": "Región de Aysén del Gral. C. Ibáñez del Campo"},
    {"codigo": "12", "nombre": "Región de Magallanes y de la Antártica Chilena"},
    {"codigo": "13", "nombre": "Región Metropolitana de Santiago"},
    {"codigo": "14", "nombre": "Región de Los Ríos"},
    {"codigo": "15", "nombre": "Región de Arica y Parinacota"},
    {"codigo": "16", "nombre": "Región de Ñuble"}
]

# Un set mínimo para funcionar ya
EMBED_COMUNAS_BY_REGION = {
    "05": [
        {"codigo": "05101", "nombre": "Valparaíso"},
        {"codigo": "05107", "nombre": "Viña del Mar"},
        {"codigo": "05109", "nombre": "Quilpué"},
        {"codigo": "05110", "nombre": "Villa Alemana"},
        {"codigo": "05111", "nombre": "Concón"}
    ],
    "13": [
        {"codigo": "13101", "nombre": "Santiago"},
        {"codigo": "13114", "nombre": "Las Condes"},
        {"codigo": "13123", "nombre": "Ñuñoa"},
        {"codigo": "13132", "nombre": "Puente Alto"},
        {"codigo": "13119", "nombre": "Maipú"}
    ]
}


def _http_get_json(url):
    last_exc = None
    for i in range(RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(0.5 * (i + 1))
    raise last_exc


def _load_json_file(path: Path, default):
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def regiones(request):
    """
    Flujo: CACHE -> API externa -> archivo local -> embebido.
    Nunca devuelve 500 si hay cualquiera de los fallbacks.
    """
    cache_key = "dpa_regiones"
    data = cache.get(cache_key)
    if data:
        return JsonResponse(data, safe=False)

    # 1) API externa
    try:
        data = _http_get_json(f"{DPA_BASE}/regiones")
        cache.set(cache_key, data, CACHE_TTL)
        return JsonResponse(data, safe=False)
    except Exception as e:
        # 2) Archivo local
        data = _load_json_file(FALLBACK_REGIONES, default=None)
        if data:
            cache.set(cache_key, data, CACHE_TTL)
            return JsonResponse(data, safe=False)

        # 3) Embebido
        data = EMBED_REGIONES
        cache.set(cache_key, data, CACHE_TTL)
        return JsonResponse(data, safe=False)


def comunas(request, region_code: str):
    """
    Flujo: CACHE -> API externa (provincias->comunas) -> archivo local -> embebido.
    """
    cache_key = f"dpa_comunas_{region_code}"
    data = cache.get(cache_key)
    if data:
        return JsonResponse(data, safe=False)

    # 1) API externa
    try:
        provincias = _http_get_json(f"{DPA_BASE}/regiones/{region_code}/provincias")
        comunas_all = []
        for p in provincias:
            c = _http_get_json(f"{DPA_BASE}/provincias/{p['codigo']}/comunas")
            comunas_all.extend(c)
        cache.set(cache_key, comunas_all, CACHE_TTL)
        return JsonResponse(comunas_all, safe=False)
    except Exception:
        # 2) Archivo local
        fb_map = _load_json_file(FALLBACK_COMUNAS_BY_REGION, default=None)
        if isinstance(fb_map, dict) and region_code in fb_map:
            cache.set(cache_key, fb_map[region_code], CACHE_TTL)
            return JsonResponse(fb_map[region_code], safe=False)

        # 3) Embebido
        if region_code in EMBED_COMUNAS_BY_REGION:
            cache.set(cache_key, EMBED_COMUNAS_BY_REGION[region_code], CACHE_TTL)
            return JsonResponse(EMBED_COMUNAS_BY_REGION[region_code], safe=False)

        # 4) Si no tenemos nada para esa región, devolvemos vacío (200)
        cache.set(cache_key, [], CACHE_TTL)
        return JsonResponse([], safe=False)
