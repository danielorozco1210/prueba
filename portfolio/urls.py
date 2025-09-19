from django.urls import path
from . import views

urlpatterns = [
    # API endpoints
    path('api/portafolios/', views.PortafolioListView.as_view(), name='portafolio-list'),
    path('api/datos-portafolio/', views.obtener_datos_portafolio, name='datos-portafolio'),
    path('api/transaccion/', views.TransaccionApi.as_view(), name='transaccion-api'),
    path('api/transaccion-legacy/', views.procesar_transaccion_legacy, name='procesar-transaccion'),
    path('api/datos-graficos/', views.datos_graficos, name='datos-graficos'),
    
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('test-api/', views.test_api_view, name='test-api'),
]