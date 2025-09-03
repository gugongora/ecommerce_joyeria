from django.shortcuts import render, get_object_or_404
from .models import Product
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
import requests
import json
from django.http import Http404
from utils.api import build_api_url
from django.conf import settings
from django.shortcuts import render, redirect
from django.utils.http import urlencode

from django.core.paginator import Paginator
from django.conf import settings





# Función para verificar si el usuario pertenece al grupo 'personal_interno'
def is_internal_person(user):
    return user.groups.filter(name='personal_interno').exists()

# Vista para listar productos, con filtros opcionales por categoría y marca
def product_list(request):
    categoria_id = request.GET.get('categoria')
    marca_id = request.GET.get('marca')

    products = Product.objects.all()
    if categoria_id:
        print("✅ Filtro aplicado: categoría", categoria_id)
        products = products.filter(category_id=categoria_id)
    if marca_id:
        print("✅ Filtro aplicado: marca", marca_id)
        products = products.filter(brand_id=marca_id)

    context = {
        'products': products,
        'API_BASE_URL': settings.API_BASE_URL,  # <- variable para el JS
    }

    return render(request, 'store/product_list.html', context)


def product_detail(request, product_id):
    url = build_api_url(f'productos/{product_id}')
    response = requests.get(url)

    if response.status_code != 200:
        return render(request, 'store/product_detail.html', {'product': None})

    product_data = response.json()
    product_data['id'] = product_id
    categoria_id = product_data.get('categoria_id') or product_data.get('categoria')  # puede ser nombre o ID

    print(f"📦 ID de categoría: {categoria_id}")

    productos_recomendados = []
    if categoria_id:
        recomendados_url = build_api_url(f'productos/?categoria={categoria_id}')
        recomendados_response = requests.get(recomendados_url)
        if recomendados_response.status_code == 200:
            response_data = recomendados_response.json()
            productos = response_data.get('results', [])  # ✅ corregido para paginación
            productos_recomendados = [p for p in productos if str(p.get('id')) != str(product_id)][:6]

    print("🧪 Productos recomendados:")
    for p in productos_recomendados:
        print("-", p)

    return render(request, 'store/product_detail.html', {
        'product': product_data,
        'productos_recomendados': productos_recomendados
    })


# Vista para búsqueda de productos por nombre
def search(request):
    query = request.GET.get('q')
    results = Product.objects.filter(name__icontains=query) if query else []
    return render(request, 'store/search_results.html', {'results': results, 'query': query})

# Dashboard protegido para grupo 'personal_interno'
@login_required
@user_passes_test(is_internal_person)
def dashboard_interno(request):
    stock_data = None
    pedido_detalle = None
    pedido_resultado = None
    sucursales = []

    # Inicia la sesión HTTP con cookies del usuario
    session = requests.Session()
    session.cookies.update(request.COOKIES)

    headers = {'Content-Type': 'application/json'}
    if 'csrftoken' in request.COOKIES:
        headers['X-CSRFToken'] = request.COOKIES['csrftoken']

    # Obtener sucursales desde API autenticada
    try:
        suc_response = session.get(build_api_url("sucursales/"), headers=headers)
        if suc_response.status_code == 200:
            data = suc_response.json()
            sucursales = data.get("results", [])
            print("⚙️ DEBUG: Sucursales cargadas:", sucursales)
        else:
            print(f"⚠️ ERROR: Status al obtener sucursales: {suc_response.status_code}")
    except Exception as e:
        print(f"❌ Excepción al obtener sucursales: {e}")

    # Procesamiento de formularios POST
    if request.method == 'POST':
        if 'consultar_stock' in request.POST:
            sucursal_id = request.POST.get('sucursal_id')
            if sucursal_id:
                url = build_api_url(f'sucursales/{sucursal_id}/stock/')
                try:
                    response = session.get(url, headers=headers)
                    if response.status_code == 200:
                        stock_data = response.json() or {'mensaje': 'No hay stock disponible.'}
                    else:
                        stock_data = {'error': f'Status {response.status_code}', 'detalle': response.text}
                except requests.RequestException as e:
                    stock_data = {'error': f'Error en la solicitud: {str(e)}'}

        elif 'consultar_pedido' in request.POST:
            pedido_id = request.POST.get('pedido_id')
            if pedido_id:
                url = build_api_url(f'pedidos/{pedido_id}/')
                try:
                    response = session.get(url, headers=headers)
                    if response.status_code == 200:
                        pedido_detalle = response.json()
                    else:
                        pedido_detalle = {'error': f'Status {response.status_code}', 'detalle': response.text}
                except requests.RequestException as e:
                    pedido_detalle = {'error': f'Error en la solicitud: {str(e)}'}

        elif 'realizar_pedido' in request.POST:
            sucursal_origen = request.POST.get('sucursal_origen')
            productos_str = request.POST.get('productos')
            observaciones = request.POST.get('observaciones', '')

            if not (sucursal_origen and productos_str):
                pedido_resultado = {'error': 'Debe completar todos los campos obligatorios.'}
            else:
                productos_items = []
                errores = []

                for item in productos_str.split(','):
                    if ':' in item:
                        codigo, cantidad = item.strip().split(':', 1)
                        try:
                            producto = Product.objects.get(codigo=codigo.strip())
                            productos_items.append({
                                'producto_codigo': producto.id,
                                'cantidad': int(cantidad.strip())
                            })
                        except Product.DoesNotExist:
                            errores.append(f'Producto "{codigo}" no encontrado.')
                        except ValueError:
                            errores.append(f'Cantidad inválida para "{codigo}".')

                if errores:
                    pedido_resultado = {'error': 'Errores al procesar productos', 'detalle': errores}
                else:
                    pedido_data = {
                        'sucursal_id': int(sucursal_origen),
                        'notas': observaciones,
                        'detalles': productos_items
                    }
                    try:
                        url = build_api_url('pedidos/')
                        response = session.post(
                            url,
                            data=json.dumps(pedido_data),
                            headers=headers
                        )
                        if response.status_code in [200, 201]:
                            pedido_resultado = response.json()
                        else:
                            pedido_resultado = {'error': f'Status {response.status_code}', 'detalle': response.text}
                    except requests.RequestException as e:
                        pedido_resultado = {'error': f'Error al enviar pedido: {str(e)}'}

    context = {
        'sucursales': sucursales,
        'stock_data': stock_data,
        'pedido_detalle': pedido_detalle,
        'pedido_resultado': pedido_resultado,
    }

    return render(request, 'store/dashboard_interno.html', context)



def quienes_somos(request):
    return render(request, 'store/quienes_somos.html')

def contacto(request):
    return render(request, 'store/contacto.html')


from utils.api import build_api_url

def catalogo_productos(request):
    # Filtros desde GET
    categoria_id = request.GET.get('categoria')
    marca_id = request.GET.get('marca')
    orden = request.GET.get('orden')
    rango_precio = request.GET.get('rango_precio')
    page_number = request.GET.get('page', 1)

    # Interpretar rango de precio
    precio_min, precio_max = None, None
    if rango_precio == "1":
        precio_max = 10000
    elif rango_precio == "2":
        precio_min = 10001
        precio_max = 40000
    elif rango_precio == "3":
        precio_min = 40001
        precio_max = 80000
    elif rango_precio == "4":
        precio_min = 80001

    # Construir parámetros
    params = {}
    if categoria_id:
        params['categoria'] = categoria_id
    if marca_id:
        params['marca'] = marca_id
    if precio_min is not None:
        params['precio_min'] = precio_min
    if precio_max is not None:
        params['precio_max'] = precio_max
    if orden:
        params['orden'] = orden

    # Consumir API
    url = build_api_url('productos/', params)
    response = requests.get(url)
    productos = response.json().get('results', []) if response.status_code == 200 else []

    paginator = Paginator(productos, 12)
    page_obj = paginator.get_page(page_number)

    # Obtener categorías y marcas
    categorias_resp = requests.get(build_api_url('categorias/'))
    marcas_resp = requests.get(build_api_url('marcas/'))
    categorias = categorias_resp.json().get('results', []) if categorias_resp.status_code == 200 else []
    marcas = marcas_resp.json().get('results', []) if marcas_resp.status_code == 200 else []

    context = {
        'page_obj': page_obj,
        'categorias': categorias,
        'marcas': marcas,
    }

    return render(request, 'store/catalogo.html', context)

def pedidos_exclusivos(request):
    return render(request, 'store/servicios/pedidos_exclusivos.html')


def argollas_matrimonio(request):
    return render(request, 'store/servicios/argollas_matrimonio.html')

def argollas_compromiso(request):
    return render(request, 'store/servicios/argollas_compromiso.html')

def reparaciones(request):
    return render(request, 'store/servicios/reparaciones.html')

def mantenimiento_relojeria(request):
    return render(request, 'store/servicios/mantenimiento_relojeria.html')

def contacto(request):
    return render(request, 'store/contacto.html')

def guia_tallas_anillos(request):
    return render(request, "store/guia_tallas_anillos.html")