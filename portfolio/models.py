from django.db import models
from decimal import Decimal

class Activo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=10, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    class Meta:
        verbose_name_plural = "Activos"

class Portafolio(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    valor_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('1000000000.00'))
    fecha_inicio = models.DateField()
    descripcion = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.nombre

class Precio(models.Model):
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='precios')
    fecha = models.DateField()
    precio = models.DecimalField(max_digits=12, decimal_places=4)
    
    class Meta:
        unique_together = ('activo', 'fecha')
        ordering = ['fecha']
    
    def __str__(self):
        return f"{self.activo.codigo} - {self.fecha}: {self.precio}"

class PesoPortafolio(models.Model):
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE, related_name='pesos')
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='pesos_portafolio')
    peso_inicial = models.DecimalField(max_digits=8, decimal_places=6)  # w_i,0
    
    class Meta:
        unique_together = ('portafolio', 'activo')
    
    def __str__(self):
        return f"{self.portafolio.nombre} - {self.activo.codigo}: {self.peso_inicial}"

class CantidadActivo(models.Model):
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE, related_name='cantidades')
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='cantidades_portafolio')
    fecha = models.DateField()
    cantidad = models.DecimalField(max_digits=15, decimal_places=4)  # c_i,t
    
    class Meta:
        unique_together = ('portafolio', 'activo', 'fecha')
        ordering = ['fecha']
    
    def __str__(self):
        return f"{self.portafolio.nombre} - {self.activo.codigo} - {self.fecha}: {self.cantidad}"

class ValorPortafolio(models.Model):
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE, related_name='valores')
    fecha = models.DateField()
    valor_total = models.DecimalField(max_digits=15, decimal_places=2)  # V_t
    
    class Meta:
        unique_together = ('portafolio', 'fecha')
        ordering = ['fecha']
    
    def __str__(self):
        return f"{self.portafolio.nombre} - {self.fecha}: {self.valor_total}"

class PesoActivo(models.Model):
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE, related_name='pesos_dinamicos')
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='pesos_dinamicos')
    fecha = models.DateField()
    peso = models.DecimalField(max_digits=8, decimal_places=6)  # w_i,t
    valor_activo = models.DecimalField(max_digits=15, decimal_places=2)  # x_i,t
    
    class Meta:
        unique_together = ('portafolio', 'activo', 'fecha')
        ordering = ['fecha']
    
    def __str__(self):
        return f"{self.portafolio.nombre} - {self.activo.codigo} - {self.fecha}: {self.peso}"

class Transaccion(models.Model):
    TIPO_CHOICES = [
        ('COMPRA', 'Compra'),
        ('VENTA', 'Venta'),
    ]
    
    portafolio = models.ForeignKey(Portafolio, on_delete=models.CASCADE, related_name='transacciones')
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name='transacciones')
    fecha = models.DateField()
    tipo = models.CharField(max_length=6, choices=TIPO_CHOICES)
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    cantidad = models.DecimalField(max_digits=15, decimal_places=4)
    
    class Meta:
        ordering = ['fecha']
    
    def __str__(self):
        return f"{self.tipo} - {self.portafolio.nombre} - {self.activo.codigo} - {self.fecha}"