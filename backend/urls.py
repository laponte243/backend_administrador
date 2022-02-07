
# Imports required for URLS.PY
from rest_framework.authtoken import views as vx
from rest_framework import routers
from django.urls import include, path
from . import views
from knox import views as knox_views
from backend.views import LoginView

# Router
router = routers.DefaultRouter()
# Utilidades
router.register(r'group', views.GroupVS)
router.register(r'permission', views.PermissionVS)
router.register(r'user', views.UserVS, basename='user')
# Utilidades
router.register(r'modulo', views.ModuloVS, basename='modulo')
router.register(r'menu', views.MenuVS, basename='menu')
router.register(r'instancia', views.InstanciaVS, basename='instancia')
router.register(r'menu-instancia', views.MenuInstanciaVS, basename='menu-instancia')
router.register(r'perfil', views.PerfilVS, basename='perfil')
router.register(r'permiso', views.PermisoVS, basename='permiso')
# Empresa
router.register(r'empresa', views.EmpresaVS, basename='empresa')
router.register(r'empresa-contacto', views.ContactoEmpresaVS, basename='empresa-contacto')
router.register(r'configuracion-papeleria', views.ConfiguracionPapeleriaVS, basename='configuracion-papeleria')
# Inventario
router.register(r'tasa-conversion', views.TasaConversionVS, basename='tasa-conversion')
router.register(r'impuesto', views.ImpuestosVS, basename='impuesto')
router.register(r'marca', views.MarcaVS, basename='marca')
router.register(r'unidad', views.UnidadVS, basename='unidad')
router.register(r'producto', views.ProductoVS, basename='producto')
router.register(r'producto-imagen', views.ProductoImagenVS, basename='producto-imagen')
router.register(r'movimiento-inventario', views.MovimientoInventarioVS, basename='Movimiento-inventario')
router.register(r'almecen', views.AlmacenVS, basename='almecen')
router.register(r'inventario', views.InventarioVS, basename='inventario')
# Ventas
router.register(r'vendedor', views.VendedorVS, basename='vendedor')
router.register(r'cliente', views.ClienteVS, basename='cliente')
router.register(r'cliente-contacto', views.ContactoClienteVS, basename='cliente-contacto')
router.register(r'pedido', views.PedidoVS, basename='pedido')
router.register(r'pedido-detalle', views.DetallePedidoVS, basename='pedido-detalle')
router.register(r'proforma', views.ProformaVS, basename='proforma')
router.register(r'proforma-detalle', views.DetalleProformaVS, basename='proforma-detalle')
router.register(r'factura', views.FacturaVS, basename='factura')
router.register(r'factura-detalle', views.DetalleFacturaVS, basename='factura-detalle')
router.register(r'lista-precio', views.ListaPrecioVS, basename='lista-precio')
router.register(r'lista-precio-detalle', views.DetalleListaPrecioVS, basename='lista-precio-detalle')
router.register(r'factura-impuesto', views.ImpuestosFacturaVS, basename='factura-impuesto')
router.register(r'factura-numerologia', views.NumerologiaFacturaVS, basename='factura-numerologia')
router.register(r'factura-nota', views.NotaFacturaVS, basename='factura-nota')
# Compras
router.register(r'proveedor', views.ProveedorVS, basename='proveedor')
router.register(r'compra', views.CompraVS, basename='compra')
router.register(r'compra-detalle', views.DetalleCompraVS, basename='compra-detalle')
router.register(r'compra-nota', views.NotaCompraVS, basename='compra-nota')

# Patterns
urlpatterns = [
    # Base
    path('', include(router.urls)),
    path('api-token-auth/', vx.obtain_auth_token),
    # Utiles
    path('create-super-user/', views.CreateSuperUser),
    path('columna-get/', views.ObtenerColumnas),
    path('menu-get/', views.ObtenerMenu),
    path('historico-get/', views.ObtenerHistorico),
    path('user-creator/', views.CrearNuevoUsuario),
    path('crear-lista/', views.crearlista),
    path('actualiza-pedido/', views.actualiza_pedido),
    # Login
    path('auth/login/', LoginView.as_view(), name='knox_login'),
    path('auth/logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('auth/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),]