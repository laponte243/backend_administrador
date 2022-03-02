# Rest's imports
from rest_framework import fields, serializers
# Django's imports
from django.contrib.auth.models import User, Permission, Group
from django.contrib.auth.forms import PasswordResetForm
from django.conf import settings
from django.utils.translation import gettext as _
# Root
from .models import *

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

            ###### USE YOUR TEXT FILE ######
            'email_template_name': 'email_text.txt',
            'request': request}
        self.reset_form.save(**opts)

###########Contenido###########


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

class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre

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
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre

class ConfiguracionPapeleriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionPapeleria
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre

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

class UnidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'
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
       return obj.fecha_vencimiento.date()

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
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
       return obj.fecha_vencimiento.date()

#ventas
class VendedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendedor
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'
    nombreVendedor = serializers.SerializerMethodField('LoadNombreVendedor')
    def LoadNombreVendedor(self, obj):
        return obj.vendedor.nombre + ' ' +'-' + ' ' + obj.vendedor.identificador
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
        return obj.empresa.nombre
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre

class ContactoClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactoCliente
        fields = '__all__'
    nombreCliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
        return obj.cliente.nombre


class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
       return obj.empresa.nombre 
    nombreCliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
       return obj.cliente.nombre 
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

class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = '__all__'
    
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
       return obj.producto.nombre 
    nombreListaPrecio = serializers.SerializerMethodField('LoadNombreListaPrecio')
    def LoadNombreListaPrecio(self, obj):
       return obj.lista_precio.nombre
    almacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
       return obj.inventario.almacen.id
    

class ProformaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proforma
        fields = '__all__'
    nombreEmpresa = serializers.SerializerMethodField('LoadNombreEmpresa')
    def LoadNombreEmpresa(self, obj):
       return obj.empresa.nombre 
    nombreCliente = serializers.SerializerMethodField('LoadNombreCliente')
    def LoadNombreCliente(self, obj):
       return obj.cliente.nombre 
    nombreVendedor = serializers.SerializerMethodField('LoadNombreVendedor')
    def LoadNombreVendedor(self, obj):
       return obj.vendedor.nombre 
    date =  serializers.SerializerMethodField('LoadDate')
    def LoadDate(self, obj):
       return obj.fecha_proforma.date()


class DetalleProformaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleProforma
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
       return obj.producto.nombre 
    nombreListaPrecio = serializers.SerializerMethodField('LoadNombreListaPrecio')
    def LoadNombreListaPrecio(self, obj):
       return obj.lista_precio.nombre
    almacen = serializers.SerializerMethodField('LoadNombreAlmacen')
    def LoadNombreAlmacen(self, obj):
       return obj.inventario.almacen.id
class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

class DetalleFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleFactura
        fields = '__all__'


class ListaPrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListaPrecio
        fields = '__all__'
    nombreInstancia = serializers.SerializerMethodField('LoadNombreInstancia')
    def LoadNombreInstancia(self, obj):
        return obj.instancia.nombre

class DetalleListaPrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleListaPrecio
        fields = '__all__'
    nombreProducto = serializers.SerializerMethodField('LoadNombreProducto')
    def LoadNombreProducto(self, obj):
        return obj.producto.nombre
    estadoProducto = serializers.SerializerMethodField('LoadEstadoProducto')
    def LoadEstadoProducto(self, obj):
        return obj.producto.activo
    precioproducto = serializers.SerializerMethodField('nprecioproducto')
    def nprecioproducto(self, obj):
       return obj.producto.costo 
    skuProductoo = serializers.SerializerMethodField('skuProducto')
    def skuProducto(self, obj):
       return obj.producto.sku 
    marcaProductoo = serializers.SerializerMethodField('marcaProducto')
    def marcaProducto(self, obj):
       return obj.producto.marca.nombre

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

#Compras
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

#Notas
class NotaFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaFactura
        fields = '__all__'

class NotaCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotaCompra
        fields = '__all__'