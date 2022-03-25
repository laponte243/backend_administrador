from django.urls import include, path
from rest_framework import routers
from . import views
from django.contrib.auth import views as auth_views

router = routers.DefaultRouter()
router.register(r'tegistro-tempera', views.RegistroTemperaturaVS)

urlpatterns = [
    path('', include(router.urls)),
    path('cambio-temperatura/', views.cambio_temp),
    path('cambio-puerta/', views.cambio_puer),
    path('errores/', views.errores),
    path('obtener-grafica/', views.obtener_grafica)
]
