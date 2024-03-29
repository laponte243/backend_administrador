# Importes requeridos para urls del backend (api)
from rest_framework.authtoken import views as vx
from rest_framework import routers
from django.urls import include, path
from knox import views as knox_views
# Raiz
from . import views
from . import views_2
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
router.register(r'configuracion-papeleria', views.CorrelativoVS, basename='configuracion-papeleria')
# Inventario
router.register(r'tasa-conversion', views.TasaConversionVS, basename='tasa-conversion')
router.register(r'impuesto', views.ImpuestosVS, basename='impuesto')
router.register(r'marca', views.MarcaVS, basename='marca')
# router.register(r'unidad', views.UnidadVS, basename='unidad')
router.register(r'producto', views.ProductoVS, basename='producto')
router.register(r'producto-imagen', views.ProductoImagenVS, basename='producto-imagen')
router.register(r'movimiento-inventario', views.MovimientoInventarioVS, basename='Movimiento-inventario')
router.register(r'almacen', views.AlmacenVS, basename='almacen')
router.register(r'inventario-detalle', views.DetalleInventarioVS, basename='inventario-detalle')
# Ventas
router.register(r'vendedor', views.VendedorVS, basename='vendedor')
router.register(r'cliente', views.ClienteVS, basename='cliente')
router.register(r'cliente-contacto', views.ContactoClienteVS, basename='cliente-contacto')
router.register(r'pedido', views.PedidoVS, basename='pedido')
router.register(r'pedido-detalle', views.DetallePedidoVS, basename='pedido-detalle')
router.register(r'proforma', views.ProformaVS, basename='proforma')
router.register(r'proforma-detalle', views.DetalleProformaVS, basename='proforma-detalle')
router.register(r'nota-devolucion', views_2.NotaDevolucionVS, basename='proforma')
router.register(r'nota-devolucion-detalle', views_2.DetalleNotaDevolucionVS, basename='proforma-detalle')
router.register(r'factura', views.FacturaVS, basename='factura')
router.register(r'factura-detalle', views.DetalleFacturaVS, basename='factura-detalle')
router.register(r'factura-impuesto', views.ImpuestosFacturaVS, basename='factura-impuesto')
router.register(r'factura-nota', views.NotaFacturaVS, basename='factura-nota')
router.register(r'notas-pago', views.NotaPagoVS, basename='notas-pago')
router.register(r'detalle-notas-pago', views.DetalleNotaPagoVS, basename='detalle-notas-pago') 
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
    path('inventario/', views.inventario),
    path('crear-usuario/', views.crear_nuevo_usuario),
    path('obtener-menu/', views.obtener_menu),
    path('obtener-columnas/', views.obtener_columnas),
    path('ventas-totales/', views.ventas_totales),
    path('permisos-disponibles/', views.permisos_disponibles),
    path('perfiles-y-usuarios/', views.perfiles_usuarios),
    path('usuario-info/', views.usuario_info),
    path('paginas-totales/', views.paginas_totales),
    path('calcular-comision/', views.comision),
    path('ubop/', views.ubop),
    path('hurt/', views_2.hurt),
    path('fact/', views_2.arreglar_facturas),
    # Guardado de registros
    path('borrar-nota/', views.borrar_nota),
    path('actualizar-nota/', views.actualizar_nota),
    path('actualizar-pedido/', views.actualizar_pedido),
    path('actualizar-proforma/', views.actualizar_proforma),
    path('validar-pedido/', views.validar_pedido),
    # path('generar-pdf-factura/<int:id_factura>/<str:token>/', views_2.generar_pdf_factura),
    path('generar-factura/', views.crear_objeto_factura),
    path('anular-factura/', views.anular_factura),
    path('guardar-configuracion-lista-precio/', views_2.guardar_configuracion_lista_precio),
    
    # Mostrar PDFs 
    path('pdf-pedido/<int:id_pedido>/<str:token>/', views.PedidoPDF.as_view()),
    path('pdf-proforma/<int:id_proforma>/<str:token>/', views.ProformaPDF.as_view()),
    path('pdf-factura/<int:id_factura>/<str:token>/', views.FacturaPDF.as_view()),
    path('pdf-factura-grande/<int:id_factura>/<str:token>/', views.FacturaGrandePDF.as_view()),
    path('pdf-nota-pago/<int:id_notapago>/<str:token>/', views.NotaPagoPDF.as_view()),
    path('pdf-proforma-guardar/', views.guardar_pdf),
    # Excels
    path('xls-generador/', views.vista_xls),
    path('subir-archivo/', views.subir_xls2),
    path('lista-precio/', views.lista_precio_xls),
    path('calcular-credito/', views.calcular_credito),
    path('analisis-vencimiento/', views_2.analisis_vencimiento),
    path('generar-lista-precio/', views_2.generar_lista_precio),
    path('libro-venta/', views_2.generar_libro_venta),
    path('historico-proforma/', views_2.generar_historico_proformas),
    path('migrar-vendedores/', views_2.migrar_vendedores),
    
    # Login
    # path('reiniciar-prioridad/', views.reiniciar_prioridad),
    path('auth/login/', LoginView.as_view(), name='knox_login'),
    path('auth/logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path('auth/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),]