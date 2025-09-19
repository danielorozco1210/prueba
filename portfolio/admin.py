from django.contrib import admin
from .models import (
    Activo, Portafolio, Precio, PesoPortafolio, 
    CantidadActivo, ValorPortafolio, PesoActivo, Transaccion
)

@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'descripcion')
    search_fields = ('codigo', 'nombre')

@admin.register(Portafolio)
class PortafolioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'valor_inicial', 'fecha_inicio')
    search_fields = ('nombre',)

@admin.register(Precio)
class PrecioAdmin(admin.ModelAdmin):
    list_display = ('activo', 'fecha', 'precio')
    list_filter = ('fecha', 'activo')
    search_fields = ('activo__codigo', 'activo__nombre')

@admin.register(PesoPortafolio)
class PesoPortafolioAdmin(admin.ModelAdmin):
    list_display = ('portafolio', 'activo', 'peso_inicial')
    list_filter = ('portafolio',)

@admin.register(CantidadActivo)
class CantidadActivoAdmin(admin.ModelAdmin):
    list_display = ('portafolio', 'activo', 'fecha', 'cantidad')
    list_filter = ('fecha', 'portafolio', 'activo')
    search_fields = ('portafolio__nombre', 'activo__codigo')

@admin.register(ValorPortafolio)
class ValorPortafolioAdmin(admin.ModelAdmin):
    list_display = ('portafolio', 'fecha', 'valor_total')
    list_filter = ('fecha', 'portafolio')

@admin.register(PesoActivo)
class PesoActivoAdmin(admin.ModelAdmin):
    list_display = ('portafolio', 'activo', 'fecha', 'peso', 'valor_activo')
    list_filter = ('fecha', 'portafolio', 'activo')

@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    list_display = ('portafolio', 'activo', 'fecha', 'tipo', 'monto', 'cantidad')
    list_filter = ('fecha', 'tipo', 'portafolio')
    search_fields = ('portafolio__nombre', 'activo__codigo')