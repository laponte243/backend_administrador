from django.urls import include, path
from rest_framework import routers
from . import views
from django.contrib.auth import views as auth_views

router = routers.DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('sign_in', views.sign_in, name='login_user'),
    path('dashboard', views.user_dashboard, name='user_dashboard'),
    path('users', views.registered_users, name='system_users'),
    path('registrar_usuario', views.sign_up, name='register_user'),
    path('activate/user/<int:user_id>', views.user_activate, name='activate_user'),
    path('deactivate/user/<int:user_id>', views.user_deactivate, name='deactivate_user'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro_temperatura', views.registros, name='registro_temperatura'),
    path('log_puertas', views.log_puerta, name='log_puertas'),
    path('cambio-temperatura/', views.cambio_temp),
    path('cambio-puerta/', views.cambio_puer),
    path('errores/', views.errores),
    path('obtener-grafica/', views.obtener_grafica)
]
