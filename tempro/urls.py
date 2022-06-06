from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'registros-temperatura', views.RegistroTemperaturaVS,basename='registro')
router.register(r'nodos', views.NodoVS, basename='nodo')
router.register(r'suscripciones', views.SuscripcionVS,basename='suscripciones')

urlpatterns = [
    path('', include(router.urls)),
    path('cambio-temperatura/', views.cambio_temp),
    path('cambio-puerta/', views.cambio_puer),
    path('errores/', views.errores),
    path('obtener-grafica/', views.obtener_grafica),
    path('promedios-tres-dias/', views.promedio_tres_dias),
    path('suscribir-usuario/', views.suscribir),
    path('ultimo-registro/', views.ultimo_registro)
]
