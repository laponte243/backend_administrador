# Registros
from django.contrib import admin
from .models import *
# Unregister
from django_rest_passwordreset.admin import *
from rest_framework.authtoken.admin import *
from knox.admin import *
# Origen
admin.site.register(Modulo)
admin.site.register(Menu)
# Contenido base
admin.site.register(Instancia)
admin.site.register(MenuInstancia)
admin.site.register(Perfil)
admin.site.register(Permiso)
admin.site.register(Empresa)
admin.site.register(ContactoEmpresa)
admin.site.register(TasaConversion)
admin.site.register(Correlativo)
admin.site.register(Impuestos)
admin.site.register(Marca)
admin.site.register(Producto)
admin.site.register(ProductoImagen)
admin.site.register(MovimientoInventario)
admin.site.register(Almacen)
admin.site.register(Inventario)
# Ventas
admin.site.register(Vendedor)
admin.site.register(Cliente)
admin.site.register(ContactoCliente)
admin.site.register(ImpuestosFactura)
admin.site.register(Proveedor)
admin.site.register(NotaFactura)
# Facturacion
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(Proforma)
admin.site.register(DetalleProforma)
admin.site.register(NotaDevolucion)
admin.site.register(DetalleNotaDevolucion)
admin.site.register(Factura)
admin.site.register(DetalleFactura)
admin.site.register(NotasPago)
admin.site.register(DetalleNotasPago)
#Compras
admin.site.register(Compra)
admin.site.register(DetalleCompra)
admin.site.register(NotaCompra)
try:
    admin.site.unregister(models.AuthToken)
    # admin.site.unregister(TokenProxy)
    admin.site.unregister(Group)
    admin.site.unregister(ResetPasswordToken)
    # admin.site.unregister(User)
except:
    pass