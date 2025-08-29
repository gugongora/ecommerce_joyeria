from rest_framework import viewsets, permissions, filters
from rest_framework.response import Response
from django.db.models import Subquery, OuterRef
from .models import Producto, Categoria, Marca, Precio
from .serializers import (
    ProductoListSerializer,
    ProductoDetailSerializer,
    CategoriaSerializer,
    MarcaSerializer
)

class ProductoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Producto.objects.all()
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'descripcion', 'codigo']
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductoDetailSerializer
        return ProductoListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Agregar campo anotado con el último precio (si no tienes precio_actual en el modelo)
        latest_price = Precio.objects.filter(producto=OuterRef('pk')).order_by('-fecha')
        queryset = queryset.annotate(
            precio_actual=Subquery(latest_price.values('valor')[:1])
        )

        # Filtros GET
        params = self.request.query_params
        categoria_id = params.get('categoria')
        marca_id = params.get('marca')
        precio_min = params.get('precio_min')
        precio_max = params.get('precio_max')
        orden = params.get('orden')

        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        if marca_id:
            queryset = queryset.filter(marca_id=marca_id)
        if precio_min:
            queryset = queryset.filter(precio_actual__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio_actual__lte=precio_max)

        # Ordenamiento
        if orden == 'precio_asc':
            queryset = queryset.order_by('precio_actual')
        elif orden == 'precio_desc':
            queryset = queryset.order_by('-precio_actual')
        elif orden == 'nombre_asc':
            queryset = queryset.order_by('nombre')
        elif orden == 'nombre_desc':
            queryset = queryset.order_by('-nombre')

        return queryset

    def get_serializer_context(self):
        return {'request': self.request}


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Categoria.objects.all().order_by('id')
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.AllowAny]


class MarcaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Marca.objects.all().order_by('id')
    serializer_class = MarcaSerializer
    permission_classes = [permissions.AllowAny]
