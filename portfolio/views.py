from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import render
from django.db import transaction
from datetime import datetime
from decimal import Decimal
from .models import (
    Portafolio, PesoActivo, ValorPortafolio, Activo, 
    CantidadActivo, Precio, Transaccion
)
from .serializers import (
    PortafolioDetalleSerializer, PesoActivoSerializer, 
    ValorPortafolioSerializer, PortafolioSerializer
)

class PortafolioListView(generics.ListAPIView):
    queryset = Portafolio.objects.all()
    serializer_class = PortafolioSerializer

@api_view(['GET'])
def obtener_datos_portafolio(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    portafolio_id = request.GET.get('portafolio_id')
    
    if not fecha_inicio or not fecha_fin:
        return Response({
            'error': 'Debe proporcionar fecha_inicio y fecha_fin en formato YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
    except ValueError:
        return Response({
            'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    portafolios_query = Portafolio.objects.all()
    if portafolio_id:
        try:
            portafolios_query = portafolios_query.filter(id=int(portafolio_id))
        except ValueError:
            return Response({
                'error': 'portafolio_id debe ser un número entero'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    resultado = []
    
    for portafolio in portafolios_query:
        valores_portafolio = ValorPortafolio.objects.filter(
            portafolio=portafolio,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).order_by('fecha')
        
        pesos_activos = PesoActivo.objects.filter(
            portafolio=portafolio,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).order_by('fecha', 'activo__codigo')
        
        resultado.append({
            'portafolio': PortafolioSerializer(portafolio).data,
            'valores_portafolio': ValorPortafolioSerializer(valores_portafolio, many=True).data,
            'pesos_activos': PesoActivoSerializer(pesos_activos, many=True).data,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        })
    
    return Response({
        'datos': resultado,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_portafolios': len(resultado)
    })

@api_view(['POST'])
def procesar_transaccion(request):
    portafolio_id = request.data.get('portafolio_id')
    fecha_str = request.data.get('fecha')
    transacciones_data = request.data.get('transacciones', [])
    
    if not all([portafolio_id, fecha_str, transacciones_data]):
        return Response({
            'error': 'Debe proporcionar portafolio_id, fecha y transacciones'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        portafolio = Portafolio.objects.get(id=portafolio_id)
    except (ValueError, Portafolio.DoesNotExist):
        return Response({
            'error': 'Fecha inválida o portafolio no encontrado'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        with transaction.atomic():
            transacciones_creadas = []
            
            for trans_data in transacciones_data:
                activo_codigo = trans_data.get('activo_codigo')
                tipo = trans_data.get('tipo')
                monto = Decimal(str(trans_data.get('monto', 0)))
                
                try:
                    activo = Activo.objects.get(codigo=activo_codigo)
                    precio = Precio.objects.get(activo=activo, fecha=fecha).precio
                    
                    if tipo == 'COMPRA':
                        cantidad = monto / precio
                    else:
                        cantidad = -(monto / precio)
                    
                    transaccion = Transaccion.objects.create(
                        portafolio=portafolio,
                        activo=activo,
                        fecha=fecha,
                        tipo=tipo,
                        monto=monto,
                        precio_unitario=precio,
                        cantidad=abs(cantidad)
                    )
                    transacciones_creadas.append(transaccion)
                    
                    actualizar_cantidades_post_transaccion(
                        portafolio, activo, fecha, cantidad
                    )
                    
                except Activo.DoesNotExist:
                    return Response({
                        'error': f'Activo {activo_codigo} no encontrado'
                    }, status=status.HTTP_400_BAD_REQUEST)
                except Precio.DoesNotExist:
                    return Response({
                        'error': f'Precio para {activo_codigo} en {fecha} no encontrado'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            recalcular_valores_historicos_desde_fecha(portafolio, fecha)
            
            return Response({
                'message': 'Transacciones procesadas exitosamente',
                'transacciones_procesadas': len(transacciones_creadas)
            })
            
    except Exception as e:
        return Response({
            'error': f'Error procesando transacciones: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def actualizar_cantidades_post_transaccion(portafolio, activo, fecha_transaccion, cambio_cantidad):
    cantidad_anterior = CantidadActivo.objects.filter(
        portafolio=portafolio,
        activo=activo,
        fecha__lt=fecha_transaccion
    ).order_by('-fecha').first()
    
    if cantidad_anterior:
        nueva_cantidad = cantidad_anterior.cantidad + cambio_cantidad
    else:
        nueva_cantidad = cambio_cantidad
    
    CantidadActivo.objects.update_or_create(
        portafolio=portafolio,
        activo=activo,
        fecha=fecha_transaccion,
        defaults={'cantidad': nueva_cantidad}
    )
    
    fechas_posteriores = Precio.objects.filter(
        activo=activo,
        fecha__gt=fecha_transaccion
    ).values_list('fecha', flat=True)
    
    for fecha in fechas_posteriores:
        CantidadActivo.objects.update_or_create(
            portafolio=portafolio,
            activo=activo,
            fecha=fecha,
            defaults={'cantidad': nueva_cantidad}
        )

def recalcular_valores_historicos_desde_fecha(portafolio, fecha_inicio):
    fechas = Precio.objects.filter(
        fecha__gte=fecha_inicio
    ).values_list('fecha', flat=True).distinct().order_by('fecha')
    
    for fecha in fechas:
        valor_total_portafolio = Decimal('0')
        
        for peso_portafolio in portafolio.pesos.all():
            activo = peso_portafolio.activo
            
            try:
                precio = Precio.objects.get(activo=activo, fecha=fecha).precio
                cantidad_obj = CantidadActivo.objects.filter(
                    portafolio=portafolio,
                    activo=activo,
                    fecha__lte=fecha
                ).order_by('-fecha').first()
                
                if cantidad_obj:
                    valor_activo = cantidad_obj.cantidad * precio
                    valor_total_portafolio += valor_activo
                    
                    PesoActivo.objects.update_or_create(
                        portafolio=portafolio,
                        activo=activo,
                        fecha=fecha,
                        defaults={
                            'peso': Decimal('0'),  # Se actualizará después
                            'valor_activo': valor_activo
                        }
                    )
                    
            except Precio.DoesNotExist:
                continue
        
        if valor_total_portafolio > 0:
            ValorPortafolio.objects.update_or_create(
                portafolio=portafolio,
                fecha=fecha,
                defaults={'valor_total': valor_total_portafolio}
            )
            
            for peso_activo in PesoActivo.objects.filter(
                portafolio=portafolio, fecha=fecha
            ):
                peso = peso_activo.valor_activo / valor_total_portafolio
                peso_activo.peso = peso
                peso_activo.save()

def dashboard_view(request):
    portafolios = Portafolio.objects.all()
    activos = Activo.objects.all()
    return render(request, 'portfolio/dashboard.html', {
        'portafolios': portafolios,
        'activos': activos
    })

@api_view(['GET'])
def datos_graficos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    portafolio_id = request.GET.get('portafolio_id')
    
    if not all([fecha_inicio, fecha_fin, portafolio_id]):
        return Response({
            'error': 'Debe proporcionar fecha_inicio, fecha_fin y portafolio_id'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        portafolio = Portafolio.objects.get(id=portafolio_id)
    except (ValueError, Portafolio.DoesNotExist):
        return Response({
            'error': 'Parámetros inválidos'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    valores = ValorPortafolio.objects.filter(
        portafolio=portafolio,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    ).order_by('fecha')
    
    datos_linea = [
        {'fecha': str(v.fecha), 'valor': float(v.valor_total)}
        for v in valores
    ]
    
    pesos = PesoActivo.objects.filter(
        portafolio=portafolio,
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin
    ).order_by('fecha', 'activo__codigo')
    
    fechas_set = set()
    activos_data = {}
    
    for peso in pesos:
        fecha_str = str(peso.fecha)
        activo_codigo = peso.activo.codigo
        
        fechas_set.add(fecha_str)
        
        if activo_codigo not in activos_data:
            activos_data[activo_codigo] = {}
        
        activos_data[activo_codigo][fecha_str] = float(peso.peso)
    
    fechas_ordenadas = sorted(list(fechas_set))
    
    datos_stacked = []
    for fecha in fechas_ordenadas:
        punto = {'fecha': fecha}
        for activo_codigo, data in activos_data.items():
            punto[activo_codigo] = data.get(fecha, 0)
        datos_stacked.append(punto)
    
    return Response({
        'datos_linea': datos_linea,
        'datos_stacked': datos_stacked,
        'activos': list(activos_data.keys()),
        'portafolio': portafolio.nombre
    })

@api_view(['POST'])
def procesar_transaccion_legacy(request):
    return Response({"detail": "Use /api/transaccion/ en su lugar"}, status=301)

def test_api_view(request):
    return render(request, 'portfolio/test_api.html')

class TransaccionApi(APIView):
    def post(self, request):
        try:
            portafolio_id = request.data["portafolio_id"]
            fecha = datetime.strptime(request.data["fecha"], "%Y-%m-%d").date()
            transacciones = request.data["transacciones"]
        except Exception:
            return Response({"detail": "JSON inválido o faltan campos."}, status=400)

        try:
            pf = Portafolio.objects.get(id=portafolio_id)
        except Portafolio.DoesNotExist:
            return Response({"detail": f"No existe portafolio id={portafolio_id}"}, status=404)

        resultados = []
        for t in transacciones:
            codigo = t.get("activo_codigo")
            tipo = t.get("tipo")
            monto = Decimal(str(t.get("monto", "0")))

            try:
                activo = Activo.objects.get(codigo=codigo)
            except Activo.DoesNotExist:
                resultados.append({"activo": codigo, "error": "Activo no encontrado"})
                continue

            try:
                precio = Precio.objects.get(activo=activo, fecha=fecha).precio
            except Precio.DoesNotExist:
                resultados.append({"activo": codigo, "error": f"No hay precio para {fecha}"})
                continue

            c_prev = CantidadActivo.objects.filter(
                portafolio=pf, activo=activo, fecha__lte=fecha
            ).order_by("-fecha").first()
            cantidad_actual = c_prev.cantidad if c_prev else Decimal("0")

            delta = monto / precio if precio != 0 else Decimal("0")
            if tipo.upper() == "VENTA":
                delta = -delta

            nueva_cantidad = cantidad_actual + delta

            CantidadActivo.objects.update_or_create(
                portafolio=pf,
                activo=activo,
                fecha=fecha,
                defaults={"cantidad": nueva_cantidad},
            )

            Transaccion.objects.create(
                portafolio=pf,
                activo=activo,
                fecha=fecha,
                tipo=tipo.upper(),
                monto=monto,
                precio_unitario=precio,
                cantidad=abs(delta)
            )

            resultados.append({
                "activo": codigo,
                "precio": str(precio),
                "delta_cantidad": str(delta),
                "nueva_cantidad": str(nueva_cantidad),
            })

        recalcular_valores_historicos_desde_fecha(pf, fecha)

        return Response({"detail": "Transacciones procesadas", "resultados": resultados}, status=200)
