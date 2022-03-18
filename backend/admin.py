from django.contrib import admin

from .models import *

admin.site.register(Modulo)
admin.site.register(Menu)
admin.site.register(Instancia)
admin.site.register(MenuInstancia)
admin.site.register(Perfil)
admin.site.register(Permiso)
admin.site.register(Empresa)
admin.site.register(ContactoEmpresa)
admin.site.register(TasaConversion)
admin.site.register(ConfiguracionPapeleria)
admin.site.register(Impuestos)
admin.site.register(Marca)
# admin.site.register(Unidad)
admin.site.register(Producto)
admin.site.register(ProductoImagen)
admin.site.register(MovimientoInventario)
admin.site.register(Almacen)
admin.site.register(Inventario)
admin.site.register(Vendedor)
admin.site.register(Cliente)
admin.site.register(ContactoCliente)


admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(Proforma)
admin.site.register(DetalleProforma)
admin.site.register(Factura)
admin.site.register(DetalleFactura)


# admin.site.register(ListaPrecio)
# admin.site.register(DetalleListaPrecio)
admin.site.register(ImpuestosFactura)
admin.site.register(NumerologiaFactura)
admin.site.register(Proveedor)
admin.site.register(Compra)
admin.site.register(DetalleCompra)
admin.site.register(NotaFactura)
admin.site.register(NotaCompra)