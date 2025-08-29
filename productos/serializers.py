# productos/serializers.py
from rest_framework import serializers
from .models import Producto, Categoria, Marca, Precio

class PrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Precio
        fields = ['fecha', 'valor']

class ProductoListSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.ReadOnlyField(source='marca.nombre')
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')
    precio_actual = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id', 'codigo', 'nombre', 'marca_nombre', 'categoria_nombre', 'precio_actual', 'imagen_url']

    def get_precio_actual(self, obj):
        precio = obj.precios.first()
        if precio:
            return precio.valor
        return None
    
    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and hasattr(obj.imagen, 'url'):
            return request.build_absolute_uri(obj.imagen.url)
        return None

class ProductoDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    marca_nombre = serializers.ReadOnlyField(source='marca.nombre')
    categoria_nombre = serializers.ReadOnlyField(source='categoria.nombre')
    categoria_id = serializers.ReadOnlyField(source='categoria.id')  # 👈 necesario para recomendaciones
    precios = PrecioSerializer(many=True, read_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'codigo', 'codigo_fabricante', 'nombre', 'descripcion',
            'marca_nombre', 'categoria_nombre', 'categoria_id',  # 👈 lo agregamos aquí
            'precios', 'imagen_url'
        ]
        
    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and hasattr(obj.imagen, 'url'):
            return request.build_absolute_uri(obj.imagen.url)
        return None

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion']

class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = ['id', 'nombre']
