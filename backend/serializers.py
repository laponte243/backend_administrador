# Importes de  Rest Api
from django.template import Origin
from rest_framework import fields, serializers
# Importes de Django
from django.contrib.auth.models import User, Permission, Group
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from django.utils.translation import gettext as _
# Raiz
from .models import *
""" Mixins modificados """
class GroupMSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'
class PermissionMSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'
class UsuarioMSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = '__all__'
        write_only_fields = ('password',)
    def create(self, validated_data):
        user = User(username = validated_data['username'], email = validated_data['email'])
        user.set_password(validated_data['password'])
        user.save()
        return user
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == 'password':
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password_reset_form_class = PasswordResetForm
    def validate_email(self, value):
        self.reset_form = self.password_reset_form_class(data=self.initial_data)
        if not self.reset_form.is_valid():
            raise serializers.ValidationError(_('Error'))
        if not User.objects.filter(email=value).exists():

            raise serializers.ValidationError(_('Invalid e-mail address'))
        return value
    def save(self):
        request = self.context.get('request')
        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL'),
            'email_template_name': 'email_text.txt',
            'request': request}
        self.reset_form.save(**opts)
""" Clases creadas para rest api """
# Contenido base
class NotaPagoMSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotasPago
        fields = '__all__'
    nombre_cliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
        return obj.cliente.nombre
    codigo_cliente = serializers.SerializerMethodField('LoadCodigoCliente')
    def LoadCodigoCliente(self, obj):
        return obj.cliente.codigo
    nombreCliente = serializers.SerializerMethodField('LoadCodigoNombreCliente')
    def LoadCodigoNombreCliente(self, obj):
        return obj.cliente.codigo + ' - ' + obj.cliente.nombre
    pre_num =  serializers.SerializerMethodField('ObtenerNumero')
    def ObtenerNumero(self, obj):
        correlativo=ConfiguracionPapeleria.objects.get(empresa=obj.cliente.empresa,tipo="N")
        print(correlativo)
        return "%s-%s"%(correlativo.prefijo if correlativo.prefijo else 'N',obj.numerologia)
class DetalleNotaPagoMSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleNotasPago
        fields = '__all__'
    cliente_nombre = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
        return obj.proforma.cliente.nombre
    cliente = serializers.SerializerMethodField('LoadCliente')
    def LoadCliente(self, obj):
        return obj.proforma.cliente.id
    pre_num =  serializers.SerializerMethodField('ObtenerNumero')
    def ObtenerNumero(self, obj):
        correlativo=ConfiguracionPapeleria.objects.get(empresa=obj.proforma.empresa,tipo="E")
        return "%s-%s"%(correlativo.prefijo,obj.proforma.numerologia)
    num_pro =  serializers.SerializerMethodField('ObtenerNumeroPro')
    def ObtenerNumeroPro(self, obj):
        return "%s"%(obj.proforma.numerologia)
class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = '__all__'
class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = '__all__'
class InstanciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instancia
        fields = '__all__'
class MenuInstanciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuInstancia
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
    nombreMenu = serializers.SerializerMethodField('LoadNombreMenu')
    def LoadNombreMenu(self, obj):
        return obj.menu.router
    nombreParent = serializers.SerializerMethodField('LoadNombreParent')
    def LoadNombreParent(self, obj):
        if obj.parent:
            return obj.parent.menu.router
        else:
            return None
class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = '__all__'
    # nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    # def LoadNombreInstancia(self, obj):
    #     return obj.instancia.nombre
class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = '__all__'
    nombreMenu = serializers.SerializerMethodField('LoadNombreMenu')
    def LoadNombreMenu(self, obj):
        return obj.menuinstancia.menu.router
    nombrePerfil = serializers.SerializerMethodField('LoadNombrePerfil')
    def LoadNombrePerfil(self, obj):
        return obj.perfil.usuario.username
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
class ContactoEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactoEmpresa
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
class TasaConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TasaConversion
        fields = '__all__'
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
       return obj.fecha_tasa.date()
class ConfiguracionPapeleriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionPapeleria
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    nombreTipo = serializers.SerializerMethodField('LoadNombreTipo')
    def LoadNombreTipo(self, obj):
        n = ''
        n = 'Nota Devolucion' if obj.tipo == 'A' else n
        n = 'Nota Control' if obj.tipo == 'B' else n
        n = 'Nota Credito' if obj.tipo == 'C' else n
        n = 'Nota Debito' if obj.tipo == 'D' else n
        n = 'Proforma' if obj.tipo == 'E' else n
        n = 'Factura' if obj.tipo == 'F' else n
        n = 'Nota Pago' if obj.tipo == 'N' else n
        n = 'Pedido' if obj.tipo == 'P' else n
        return n

class ImpuestosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impuestos
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'
    precio_1 = serializers.SerializerMethodField('LoadPrecio1')
    def LoadPrecio1(self, obj):
        return round(obj.precio_1,2)
    precio_2 = serializers.SerializerMethodField('LoadPrecio2')
    def LoadPrecio2(self, obj):
        return round(obj.precio_2,2)
    precio_3 = serializers.SerializerMethodField('LoadPrecio3')
    def LoadPrecio3(self, obj):
        return round(obj.precio_3,2)
    precio_4 = serializers.SerializerMethodField('LoadPrecio4')
    def LoadPrecio4(self, obj):
        return round(obj.precio_4,2)
    nombreMarca = serializers.SerializerMethodField('LoadNombreMarca')
    def LoadNombreMarca(self, obj):
        return obj.marca.nombre
    nombreCodigo = serializers.SerializerMethodField('nombreCodigoo')
    def nombreCodigoo(self, obj):
        return obj.sku + ' ' + '-'+ ' ' + obj.nombre
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
class ProductoImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoImagen
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
        return obj.producto.nombre
class MovimientoInventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoInventario
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
        return obj.producto.nombre
    nombreAlmacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
        return obj.almacen.nombre
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
        if obj.fecha_vencimiento:
            return obj.fecha_vencimiento.date()
        return None
class AlmacenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Almacen
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
class InventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventario
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
        return obj.producto.nombre
    nombreAlmacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
        return obj.almacen.nombre
    lote_cantidad = serializers.SerializerMethodField('LoadLote')
    def LoadLote(self,obj):
        return 'Lote: ' + obj.lote + ' - ' + 'Cantidad: ' + str(obj.disponible)
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
        return obj.fecha_vencimiento.date()
# Ventas 
class VendedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendedor
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
    code_nomb = serializers.SerializerMethodField('LoadNumeroNombre')
    def LoadNumeroNombre(self, obj):
        return "%s - %s"%(obj.codigo,obj.nombre)

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'
    nombreVendedor = serializers.SerializerMethodField('LoadNombreVendedor')
    def LoadNombreVendedor(self, obj):
        if obj.vendedor.identificador:
            return obj.vendedor.nombre + ' ' +'-' + ' ' + obj.vendedor.identificador
        return obj.vendedor.nombre
    codigoVendedor = serializers.SerializerMethodField('LoadCodigoVendedor')
    def LoadCodigoVendedor(self, obj):
        return obj.vendedor.codigo
    codigoNombreCliente = serializers.SerializerMethodField('LoadCodigoNombreCliente')
    def LoadCodigoNombreCliente(self, obj):
        if obj.codigo:
            return obj.codigo + ' - ' + obj.nombre
        return obj.nombre
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
    saldo_pendiente = serializers.SerializerMethodField('loadSaldo')
    def loadSaldo(self, obj):
            proforma = Proforma.objects.filter(cliente=obj.id)
            saldo = 0.0
            for i in proforma:
                saldo += i.saldo_proforma
            return saldo
class ContactoClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactoCliente
        fields = '__all__'
    nombre_cliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
        return obj.cliente.nombre
    nombreCliente = serializers.SerializerMethodField('LoadCodigoNombreCliente')
    def LoadCodigoNombreCliente(self, obj):
        return obj.cliente.codigo + ' - ' + obj.cliente.nombre
class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    codigo_cliente = serializers.SerializerMethodField('LoadCodigoCliente')
    def LoadCodigoCliente(self, obj):
        return obj.cliente.codigo
    nombre_cliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
        return obj.cliente.nombre
    nombreCliente = serializers.SerializerMethodField('LoadCodigoNombreCliente')
    def LoadCodigoNombreCliente(self, obj):
        return obj.cliente.codigo + ' - ' + obj.cliente.nombre
    identificador_fiscal = serializers.SerializerMethodField('LoadIdentificadorCliente')
    def LoadIdentificadorCliente(self, obj):
        return obj.cliente.identificador 
    nombreVendedor = serializers.SerializerMethodField('LoadNombreVendedor')
    def LoadNombreVendedor(self, obj):
        return obj.vendedor.nombre 
    Cliente_direccion = serializers.SerializerMethodField('nombreCliente_Vendedoor')
    def nombreCliente_Vendedoor(self, obj):
        return obj.cliente.ubicacion 
    Cliente_telefono = serializers.SerializerMethodField('Cliente_telefonoo')
    def Cliente_telefonoo(self, obj):
        return obj.cliente.telefono 
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
        return obj.fecha_pedido.date()
    time =  serializers.SerializerMethodField('Loadtime')
    def Loadtime(self, obj):
        return obj.fecha_pedido.time()
    pre_num =  serializers.SerializerMethodField('ObtenerNumero')
    def ObtenerNumero(self, obj):
        correlativo=ConfiguracionPapeleria.objects.get(empresa=obj.empresa,tipo="P")
        return "%s-%s"%(correlativo.prefijo,obj.numerologia)
class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
       return obj.producto.nombre
    almacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
        inventario = obj.inventario
        if inventario:
            return inventario.almacen.id
        return None
    vencimiento = serializers.SerializerMethodField('LoadVencimiento')
    def LoadVencimiento(self, obj):
        inventario = obj.inventario
        if inventario:
            return inventario.fecha_vencimiento.date()
        return None
class ProformaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proforma
        fields = '__all__'
    factura = serializers.SerializerMethodField('LoadFactura')
    def LoadFactura(self, obj):
        try:
            return Factura.objects.filter(proforma=obj.id).first().id
        except:
            return None
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    codigo_cliente = serializers.SerializerMethodField('LoadCodigoCliente')
    def LoadCodigoCliente(self, obj):
        return obj.cliente.codigo
    nombre_cliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
        return obj.cliente.nombre
    nombreCliente = serializers.SerializerMethodField('LoadCodigoNombreCliente')
    def LoadCodigoNombreCliente(self, obj):
        return obj.cliente.codigo + ' - ' + obj.cliente.nombre
    nombreVendedor = serializers.SerializerMethodField('LoadNombreVendedor')
    def LoadNombreVendedor(self, obj):
        return obj.vendedor.nombre
    codigoVendedor = serializers.SerializerMethodField('LoadNumeroVendedor')
    def LoadNumeroVendedor(self, obj):
        return obj.vendedor.codigo
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
        return obj.fecha_proforma.date()
    date_despacho = serializers.SerializerMethodField('LoadDateDespacho')
    def LoadDateDespacho(self, obj):
        if obj.fecha_despacho:
            return obj.fecha_despacho.date()
        return ''
    pre_num =  serializers.SerializerMethodField('ObtenerNumero')
    def ObtenerNumero(self, obj):
        correlativo=ConfiguracionPapeleria.objects.get(empresa=obj.empresa,tipo="E")
        return "%s-%s"%(correlativo.prefijo,obj.numerologia)
class DetalleProformaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleProforma
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
       return obj.producto.nombre 
    almacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
        inventario = obj.inventario
        if inventario:
            return inventario.almacen.id
        return None
    vencimiento = serializers.SerializerMethodField('LoadVencimiento')
    def LoadVencimiento(self, obj):
        inventario = obj.inventario
        if inventario:
            return inventario.fecha_vencimiento.date()
        return None

class NotaDevolucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaDevolucion
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    codigo_cliente = serializers.SerializerMethodField('LoadCodigoCliente')
    def LoadCodigoCliente(self, obj):
        return obj.cliente.codigo
    nombre_cliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
        return obj.cliente.nombre
    nombreCliente = serializers.SerializerMethodField('LoadCodigoNombreCliente')
    def LoadCodigoNombreCliente(self, obj):
        return obj.cliente.codigo + ' - ' + obj.cliente.nombre
    nombreVendedor = serializers.SerializerMethodField('LoadNombreVendedor')
    def LoadNombreVendedor(self, obj):
        return obj.vendedor.nombre
    codigoVendedor = serializers.SerializerMethodField('LoadNumeroVendedor')
    def LoadNumeroVendedor(self, obj):
        return obj.vendedor.codigo
    pre_num =  serializers.SerializerMethodField('ObtenerNumero')
    def ObtenerNumero(self, obj):
        correlativo=ConfiguracionPapeleria.objects.get(empresa=obj.empresa,tipo="E")
        return "%s-%s"%(correlativo.prefijo,obj.numerologia)
class DetalleNotaDevolucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleNotaDevolucion
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
       return obj.producto.nombre 
    almacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
        inventario = obj.inventario
        if inventario:
            return inventario.almacen.id
        return None
class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
       return obj.fecha_factura.date()
    pre_num =  serializers.SerializerMethodField('ObtenerNumero')
    def ObtenerNumero(self, obj):
        if obj.origen:
            proforma = Proforma.objects.get(id=obj.origen)
        else:
            proforma = Proforma.objects.filter(id=obj.proforma.id).first()
        correlativo=ConfiguracionPapeleria.objects.get(empresa=proforma.empresa,tipo="F")
        return "%s%s"%(correlativo.prefijo+'-',obj.numerologia)
class DetalleFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleFactura
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
       return obj.producto.nombre
    almacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
        inventario = obj.inventario
        if inventario:
            return inventario.almacen.id
        return None
    vencimiento = serializers.SerializerMethodField('LoadVencimiento')
    def LoadVencimiento(self, obj):
        inventario = obj.inventario
        if inventario:
            return inventario.fecha_vencimiento.date()
        return None
class ImpuestosFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpuestosFactura
        fields = '__all__'
    nombreFactura = serializers.SerializerMethodField('LoadNombreFactura')
    def LoadNombreProducto(self, obj):
        return obj.venta.nombre
class NumerologiaFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = NumerologiaFactura
        fields = '__all__'
    nombreFactura = serializers.SerializerMethodField('LoadNombreFactura')
    def LoadNombreProducto(self, obj):
        return obj.venta.nombre
class NotaFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaFactura
        fields = '__all__'
# Compras
class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    nombreMarcas = serializers.SerializerMethodField('LoadNombreMarcas')
    def LoadNombreMarcas(self, obj):
        nombres = ''
        for id in obj.marcas.all():
            nombres += id.nombre + ',' + ' '
        return nombres
class CompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compra
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    nombreProveedor = serializers.SerializerMethodField('LoadNombreProveedor')
    def LoadNombreProveedor(self, obj):
        return obj.Proveedor.nombre
class DetalleCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleCompra
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
        return obj.producto.nombre
class NotaCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaCompra
        fields = '__all__'