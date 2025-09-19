from rest_framework import serializers
from .models import Activo, Portafolio, PesoActivo, ValorPortafolio

class ActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Activo
        fields = ['id', 'codigo', 'nombre', 'descripcion']

class PortafolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portafolio
        fields = ['id', 'nombre', 'valor_inicial', 'fecha_inicio', 'descripcion']

class PesoActivoSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source='activo.codigo', read_only=True)
    activo_nombre = serializers.CharField(source='activo.nombre', read_only=True)
    portafolio_nombre = serializers.CharField(source='portafolio.nombre', read_only=True)
    
    class Meta:
        model = PesoActivo
        fields = ['id', 'portafolio_nombre', 'activo_codigo', 'activo_nombre', 
                 'fecha', 'peso', 'valor_activo']

class ValorPortafolioSerializer(serializers.ModelSerializer):
    portafolio_nombre = serializers.CharField(source='portafolio.nombre', read_only=True)
    
    class Meta:
        model = ValorPortafolio
        fields = ['id', 'portafolio_nombre', 'fecha', 'valor_total']

class PortafolioDetalleSerializer(serializers.Serializer):
    portafolio = PortafolioSerializer(read_only=True)
    valores_portafolio = ValorPortafolioSerializer(many=True, read_only=True)
    pesos_activos = PesoActivoSerializer(many=True, read_only=True)
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()