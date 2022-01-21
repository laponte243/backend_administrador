# Django's imports
from typing_extensions import TypeGuard
from django.db import models
from django.contrib.auth.models import User
from django.db.models.deletion import DO_NOTHING
from django.db.models.fields import TextField
# Simple history
from simple_history.models import HistoricalRecords

#Utiles

class Modulo(models.Model):
    nombre = models.TextField(max_length=20,blank=False,null=False)
    history = HistoricalRecords()
    def __str__(self):
        return '%s' % (self.nombre)

class Menu(models.Model):
    router = models.CharField(max_length=150, blank=False, null=False, help_text="Nombre la opcion de menú")
    parent = models.ForeignKey('self', null=True, blank=False, on_delete=models.DO_NOTHING, help_text="Si el menu es hijo de otro")
    orden = models.IntegerField(null=False, default=0)
    modulos = models.ManyToManyField(Modulo, blank=False)
    history = HistoricalRecords()
    def __str__(self):
        return '%s' % (self.router)

# Instancia
class Instancia(models.Model):
    nombre = models.TextField(max_length=150,blank=False,null=False,help_text="Nombre de la instancia")
    activo = models.BooleanField(default=True,help_text="esta la instancia activa?")
    multiempresa = models.BooleanField(default=True,help_text="esta la instancia es multiempresa?")
    vencimiento = models.DateTimeField(null=True,blank=False,help_text="Fecha de vencimiento de la instancia")
    modulos = models.ManyToManyField(Modulo, blank=False)
    history = HistoricalRecords()
    def __str__(self):
        return '%s' % (self.nombre)

class MenuInstancia(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    menu = models.ForeignKey(Menu, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="SuperMenu asociado")   

    parent = models.ForeignKey('self', null=True, blank=False, on_delete=models.DO_NOTHING, help_text="Si el menu es hijo de otro")
    orden = models.IntegerField(null=False, default=0)
    history = HistoricalRecords()
    def __str__(self):
        if (self.parent == None):
            return '[%s] / %s' % (self.instancia.nombre, self.menu.router)
        else:
            return '[%s] / %s, %s' % (self.instancia.nombre, self.menu.parent.router, self.menu.router)

class Perfil(models.Model):
    TIPO = (
        ('S', 'Super'),
        ('A', 'Admin'),
        ('U', 'Usuario'),
        ('V', 'Vendedor'),
    )
    instancia = models.ForeignKey(Instancia, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, help_text="usuario asociado")
    activo = models.BooleanField(default=True, help_text="esta el usuario activo?")
    avatar = models.ImageField(upload_to='avatars', null=True, help_text="avatar para el usuario")
    tipo = models.CharField(max_length=1, null=True, choices=TIPO, default='U', help_text="Tipo de usuario")
    history = HistoricalRecords()
    def __str__(self):
        return '%s - %s - %s' % (self.instancia.nombre,self.usuario.username,self.tipo)

class Permiso(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    
    menuinstancia = models.ForeignKey(MenuInstancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Opcion de menu asociada")
    perfil = models.ForeignKey(Perfil, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Usuario asociado")
    
    leer = models.BooleanField(default=True, help_text="Tiene opcion de leer?")
    escribir = models.BooleanField(default=True, help_text="Tiene opcion de escribir?")
    borrar = models.BooleanField(default=True, help_text="Tiene opcion de borrar?")
    actualizar = models.BooleanField(default=True, help_text="Tiene opcion de actualizar?")

    history = HistoricalRecords()
    def __str__(self):
        return '%s - %s - %s' % (self.instancia.nombre,self.menuinstancia.menu.router,self.perfil.usuario.username)

class Nota(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    TIPO = (
        ('C', 'Credito'),
        ('D', 'Debito'),
    )
    subtotal = models.FloatField(null=False, default=0, blank=False, help_text="subtotal de la nota")
    descripcion = models.TextField(max_length=150, blank=False, null=True, help_text="descripcion del caso de la nota")
    tipo = models.CharField(max_length=1, choices=TIPO, default='C', help_text="que tipo de nota es")
    fecha = models.DateTimeField(auto_now_add=True, help_text="fecha de la nota")
    
    class Meta:
        abstract=True

# Empresa
class Empresa(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    nombre = models.TextField(max_length=150, blank=False, null=False, help_text="Razon social de la empresa")
    direccion_fiscal = models.TextField(max_length=150, blank=False, null=False, help_text="direccion fiscal de la empresa")
    logo = models.ImageField(upload_to='empresas', null=True, help_text="logo de la empresa")
    history = HistoricalRecords()

class ContactoEmpresa(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    empresa = models.ForeignKey(Empresa, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="empresa asociada")
    nombre = models.TextField(max_length=150, blank=False, null=False, help_text="nombre del contacto")
    telefono = models.TextField(max_length=150, blank=False, null=False, help_text="telefono del contacto")
    mail = models.TextField(max_length=150, blank=False, null=False, help_text="correo electronico del contacto")

class ConfiguracionPapeleria(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    TIPO = (
        ('F', 'Factura'),
        ('N', 'Nota entrega'),
        ('C', 'Nota credito'),
        ('D', 'Nota debito'),
    )
    empresa = models.ForeignKey(Empresa, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="empresa asociada")
    prefijo = models.TextField(max_length=10, blank=True, null=True, help_text="prefijo para el numero")
    formato = models.TextField(max_length=20, blank=True, null=True, help_text="formato de numero con 0 adelante 0000000")
    valor = models.IntegerField(blank=False, null=False, help_text="valor actual del numero")
    tipo = models.CharField(max_length=1, choices=TIPO, default='F', help_text="tipo de numero")

#Inventario

class TasaConversion(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    fecha_tasa = models.DateTimeField(auto_now_add=True, help_text="tasa de conversion del dia")
    valor = models.FloatField(blank=False, null=False, help_text="valor de la tasa de conversion")

class Impuestos(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    nombre = models.TextField(max_length=30, blank=False, null=False, help_text="Nombre del impuesto")
    producto = models.BooleanField(default=False, help_text="afecta a solo ciertos productos?")
    activo = models.BooleanField(default=False, help_text="esta activo?")
    modificador = models.FloatField(blank=False, help_text="Cual es el porcentaje modificador de subtotal")
    regla = models.BooleanField(default=False, help_text="tiene una regla?")
    min = models.FloatField(blank=False, null=True, help_text="Cual es el valor minimo en subtotal")
    max = models.FloatField(blank=False, null=True, help_text="cual es el valor maximo en subtotal")
    history = HistoricalRecords()

class Marca(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    nombre = models.TextField(max_length=220, blank=True, help_text="Nombre de la marca")
    logo = models.ImageField(upload_to='marcas', null=True, help_text="logo de la marca")
    history = HistoricalRecords()

class Unidad(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    nombre = models.TextField(max_length=30, blank=False, help_text="Nombre de la unidad de medida")
    abreviatura = models.TextField(max_length=10, blank=False, help_text="Abreviatura de la unidad de medida")
    history = HistoricalRecords()

class Producto(models.Model):
    #datos basicos
    instancia = models.ForeignKey(Instancia, null=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    unidad = models.ForeignKey(Unidad, null=True, on_delete=models.DO_NOTHING, help_text="Unidad de medida del producto")
    marca = models.ForeignKey(Marca, null=True, on_delete=models.DO_NOTHING, help_text="Marca asociada al producto")
    nombre = models.TextField(max_length=150, null=True, blank=True, help_text="Nombre del producto")
    sku = models.TextField(max_length=150, null=False, blank=False, help_text="SKU del producto")
    servicio = models.BooleanField(default=False, help_text="¿Es un servicio?")
    lote_producto = models.BooleanField(default=False, help_text="¿Esta en un lote?")
    #datos financieros
    costo = models.FloatField(null=True, help_text="Costo del producto")
    exonerado = models.BooleanField(default=False, help_text="¿Esta exonerado el impuesto?")
    venta_sin_inventario = models.BooleanField(default=False, help_text="¿Se permite la venta del producto sin inventario?")
    #datos configuracion
    activo = models.BooleanField(default=True, help_text="¿El producto esta activo?")
    menejo_inventario = models.BooleanField(default=True, help_text="¿Se manejara inventario del producto?")
    venta = models.BooleanField(default=True, help_text="¿Es un producto que se puede vender?")
    history = HistoricalRecords()

class ProductoImagen(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    producto = models.ForeignKey(Producto, null=True, on_delete=models.DO_NOTHING, help_text="Producto asociado")
    imagen = models.ImageField(upload_to='productos', help_text="Imagen del producto")
    principal = models.BooleanField(default=False, help_text="Es la imagen principal del producto?")
    history = HistoricalRecords()

class Lote(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    producto = models.ForeignKey(Producto, null=False, on_delete=models.DO_NOTHING, help_text="Producto base del lote")
    cantidad_recepcion = models.FloatField(null=True, help_text="Cantidad de recepcion del producto")
    fecha_vencimiento = models.DateField(null=False, help_text="Fecha de vencimiento del producto")
    numero_lote = models.IntegerField(null=True, help_text="Numero de lote del producto")
    cantida_disponible = models.FloatField(null=False, help_text="Cantidad disponible del producto")
    history = HistoricalRecords() # colocar como registro

class Almacen(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    nombre = models.TextField(max_length=220, blank=True, help_text="Nombre del almacen")
    activo = models.BooleanField(default=False, help_text="El almacen esta activo?")
    history = HistoricalRecords()

class Inventario(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    producto = models.ForeignKey(Producto, null=False, on_delete=models.DO_NOTHING, help_text="producto asociado")
    almacen = models.ForeignKey(Almacen, null=True, on_delete=models.DO_NOTHING, help_text="almacen asociado")
    disponible = models.FloatField(null=False, default=0, blank=False, help_text="cantidad disponible")
    transito = models.FloatField(null=False, default=0, blank=False, help_text="cantidad en transito")
    bloqueado = models.FloatField(null=False, default=0, blank=False, help_text="cantidad bloqueada")
    min = models.FloatField(null=True, help_text="Cantidad minima")
    max = models.FloatField(null=True, help_text="Cantidad maxima")
    history = HistoricalRecords()

#Ventas
class Vendedor(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    nombre = models.TextField(max_length=150, blank=True, help_text="nombre completo del vendedor")
    identificador = models.TextField(max_length=150, blank=True, help_text="nombre completo del vendedor")
    telefono = models.TextField(max_length=150, blank=True, help_text="telefono del vendedor")
    correo = models.TextField(max_length=150, blank=True, help_text="correo asociado al vendedor")
    activo = models.BooleanField(default=False, help_text="Esta activo?")
    history = HistoricalRecords()

class Cliente(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    vendedor = models.ForeignKey(Vendedor, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="vendedor asociado")
    nombre = models.TextField(max_length=150, blank=True, help_text="Razon social del cliente")
    identificador = models.TextField(max_length=150, blank=True, help_text="Numero de indentificacion fiscal")
    ubicacion = models.TextField(max_length=150, blank=True, help_text="Ubicacion o direccion del cliente")
    credito = models.BooleanField(default=False, help_text="Se le puede vender a credito?")
    imagen = models.ImageField(upload_to='clientes', null=True, help_text="Imagen o logo asociado al cliente")
    activo = models.BooleanField(default=False, help_text="Esta activo?")
    history = HistoricalRecords()

class ContactoCliente(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    cliente = models.ForeignKey(Cliente, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Cliente asociado")
    nombre = models.TextField(max_length=150, blank=False, null=False, help_text="Nombre del contacto")
    telefono = models.TextField(max_length=150, blank=False, null=False, help_text="telefono del contacto")
    mail = models.TextField(max_length=150, blank=False, null=False, help_text="correo electronico del contacto")

class ListaPrecio(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    nombre = models.TextField(max_length=150, blank=False, null=True, help_text="nombre de la lista de precios?")
    activo = models.BooleanField(default=True, help_text="esta lista de precios esta activa?")

class DetalleListaPrecio(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    listaprecio = models.ForeignKey(ListaPrecio, null=False, blank=False, on_delete=models.DO_NOTHING,help_text="Lista de precio asociada")

    producto = models.ForeignKey(Producto, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="producto asociado")
    precio = models.FloatField(null=False, default=0, blank=False, help_text="precio del producto en la lista")

    history = HistoricalRecords()

class Pedido(models.Model): # Pedido 
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    empresa = models.ForeignKey(Empresa, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="empresa asociada")
    cliente = models.ForeignKey(Cliente, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="cliente asociado")
    vendedor = models.ForeignKey(Vendedor, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="vendedor asociado")
    fecha_pedido = models.DateTimeField(auto_now_add=True, help_text="fecha de generacion del pedido")

    history = HistoricalRecords()

class DetallePedido(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    pedido = models.ForeignKey(Pedido, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="pedido asociado")

    producto = models.ForeignKey(Producto, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="producto asociado")
    cantidad = models.FloatField(null=False, default=0, blank=False, help_text="Cantidad vendida")
    
    history = HistoricalRecords()

class Proforma(models.Model):
    pedido = models.ForeignKey(Pedido, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="pedido asociado")
    empresa = models.ForeignKey(Empresa, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="empresa asociada")
    cliente = models.ForeignKey(Cliente, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="cliente asociado")
    vendedor = models.ForeignKey(Vendedor, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="vendedor asociado")
    
    nombre_cliente = models.TextField(max_length=150, blank=False, null=False, help_text="Nombre del cliente en la proforma")
    identificador_fiscal = models.TextField(max_length=150, blank=False, null=False, help_text="Identificador fiscal del cliente en la venta")
    direccion_cliente = models.TextField(max_length=150, blank=False, null=False, help_text="telefono del cliente en la proforma")
    telefono_cliente = models.TextField(max_length=150, blank=False, null=False, help_text="fecha de generacion de la proforma")

    subtotal = models.FloatField(null=False, default=0, blank=False, help_text="subtotal de la proforma")
    monto_exento = models.FloatField(null=False, default=0, blank=False, help_text="monto exento de la proforma")
    impuesto = models.FloatField(null=False, default=0, blank=False, help_text="impuesto")
    total = models.FloatField(null=False, default=0, blank=False, help_text="total de la proforma")
    
    nota_entrega = models.TextField(default=False, help_text="fecha de generacion una nota de entrega?")

    history = HistoricalRecords()

class DetalleProforma(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    proforma = models.ForeignKey(Proforma, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="proforma asociada")
    producto = models.ForeignKey(Producto, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="detallepedido asociada")
    lote_producto = models.ForeignKey(Lote, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Lote del producto asociado")

    descripcion = models.TextField(max_length=150, blank=False, null=True, help_text="En caso de no tener un producto asociado se puede colocar una descripcion del rublo acá")
    precio = models.TextField(null=False, default=0, blank=False, help_text="precio del producto o servicio a vender")
    subtotal = models.TextField(null=False, default=0, blank=False, help_text="Precio por la cantidad del producto")

    inventario = models.TextField(default=True, help_text="La venta afecta el inventario?")
    history = HistoricalRecords()

class Factura(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    pedido = models.ForeignKey(Pedido, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="pedido asociado")
    proforma = models.ForeignKey(Proforma, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="proforma asociada")
    #Datos fijos de la factura
    nombre_empresa = models.TextField(
        max_length=150, null=False, blank=False, help_text="empresa asociada")
    telefonocontacto_empresa = models.TextField(
        max_length=150, null=False, blank=False, help_text="empresa asociada")
    direccion_empresa = models.TextField(
        max_length=150, null=False, blank=False, help_text="empresa asociada")
    
    nombre_cliente = models.TextField(
        max_length=150, blank=False, null=False, help_text="Nombre del cliente en la venta")
    identificador_fiscal = models.TextField(
        max_length=150, blank=False, null=False, help_text="Identificador fiscal del cliente en la venta")
    direccion_cliente = models.TextField(
        max_length=150, blank=False, null=False, help_text="telefono del cliente en la venta")
    telefono_cliente = models.TextField(
        max_length=150, null=False, blank=False, help_text="empresa asociada")

    nombre_vendedor = models.TextField(
        max_length=150, null=True, blank=False, help_text="vendedor asociado")
    telefono_vendedor = models.TextField(
        max_length=150, null=False, blank=False, help_text="empresa asociada")
    
    fecha_factura = models.TextField(
        max_length=150, blank=False, null=False, help_text="fecha de generacion de la venta")
    subtotal = models.TextField(
        max_length=150, null=False, default=0, blank=False, help_text="subtotal de la venta")
    monto_exento = models.TextField(
        max_length=150,null=False, default=0, blank=False, help_text="monto exento de la proforma")
    impuesto = models.TextField(
        max_length=150, null=False, default=0, blank=False, help_text="monto exento de la proforma")
    total = models.TextField(
        max_length=150, null=False, default=0, blank=False, help_text="total de la venta")
    #Datos de pago
    tipo_pago = models.TextField(
        max_length=150, blank=False, null=False, help_text="tipo de pago utilizado por el cliente de la venta")
    credito = models.TextField(
        default=False, help_text="La venta se realizo a credito?")
    dias_credito = models.TextField(
        null=True, default=0, help_text="dias de credito?")
    #Estatus
    nota_entrega = models.TextField(
        default=False, help_text="fecha de generacion una nota de entrega?")
    history = HistoricalRecords()

class DetalleFactura(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    factura = models.ForeignKey(Factura, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="venta asociada")
    lote = models.ForeignKey(Lote, null=False, blank=False, on_delete=DO_NOTHING, help_text="Lote asociado del producto")
    #Datos fijos
    lote_producto = models.TextField(
        max_length=150, null=True, blank=False, help_text="Lote fijo asociado del producto asociado")
    fecha_vencimiento = models.TextField(
        max_length=150, null=True, blank=False, help_text="Fecha de vencimiento del lote")
    producto = models.TextField(
        max_length=150, null=False, blank=False, help_text="producto asociado")
    descripcion = models.TextField(
        max_length=150, blank=False, null=True, help_text="En caso de no tener un producto asociado se puede colocar una descripcion del rublo aca")
    cantidad = models.TextField(
        max_length=150, default=True, help_text="La venta afecta el inventario?")
    precio = models.TextField(
        max_length=150, null=False, default=0, blank=False, help_text="precio del producto o servicio a vender")
    subtotal = models.TextField(
        max_length=150, null=False, default=0, blank=False, help_text="subtotal del producto")
    history = HistoricalRecords()

class ImpuestosFactura(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    factura = models.ForeignKey(Factura, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="venta asociada")
    nombre = models.TextField(max_length=100, blank=False, null=True, help_text="nombre del impuesto asociado")
    subtotal = models.FloatField(null=False, default=0, blank=False, help_text="subtotal del impuesto asociado a la venta")
    history = HistoricalRecords()

class NumerologiaFactura(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    factura = models.ForeignKey(Factura, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="venta asociada")
    tipo = models.TextField(max_length=100, blank=False, null=True, help_text="tipo de numerologia")
    valor = models.TextField(max_length=100, blank=False, null=True, help_text="valor que se utilizo en la venta")
    history = HistoricalRecords()

class NotaFactura(Nota):
    factura = models.ForeignKey(Factura, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="venta asociada")
    history = HistoricalRecords()

#Compras
class Proveedor(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    empresa = models.ForeignKey(Empresa, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="empresa asociada")
    marcas = models.ManyToManyField(Marca, help_text="marcas asociadas")
    nombre = models.TextField(max_length=150, blank=True, help_text="nombre del proveedor")
    identificador = models.TextField(max_length=150, blank=True, help_text="identificador fiscal asociado")
    ubicacion = models.TextField(max_length=150, blank=True, help_text="Ubicacion del proveedor")
    credito = models.BooleanField(default=False, help_text="el proveedor da credito?")
    imagen = models.ImageField(upload_to='proveedores', null=True, help_text="imagen asociada al proveedor")
    history = HistoricalRecords()

class Compra(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    empresa = models.ForeignKey(Empresa, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="empresa asociada")
    Proveedor = models.ForeignKey(Cliente, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="proveedor asoaciado")
    #datos fijos factura
    fecha_factura = models.DateTimeField(auto_now_add=True, help_text="fecha de la factura de compra")
    numero_factura = models.TextField(max_length=150, blank=False, null=False, help_text="numero de la factura")
    numero_control = models.TextField(max_length=150, blank=False, null=True, help_text="numero de control")
    subtotal = models.FloatField(null=False, default=0, blank=False, help_text="subtotal de la factura")
    impuestos = models.FloatField(null=False, default=0, blank=False, help_text="total en impuestos")
    total = models.FloatField(null=False, default=0, blank=False, help_text="total en factura")
    #datos pago
    tipo_pago = models.TextField(max_length=150, blank=False, null=False, help_text="tipo de pago utilizado")
    credito = models.BooleanField(default=False, help_text="la factura es a credito?")
    dias_credito = models.IntegerField(null=True, default=0, help_text="cuantos dias de credito?")
    history = HistoricalRecords()

class DetalleCompra(models.Model):
    instancia = models.ForeignKey(Instancia, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="Instancia asociada")
    compra = models.ForeignKey(Compra, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="compra asociada")
    producto = models.ForeignKey(Producto, null=True, blank=False, on_delete=models.DO_NOTHING, help_text="producto asociado")
    descripcion = models.TextField(max_length=150, blank=False, null=True, help_text="en caso de no tener producto asociado a la compra se puede colocar una descripcion del rubro")
    cantidad = models.FloatField(null=False, default=0, blank=False, help_text="cantidad comprada")
    servicio = models.BooleanField(default=False, help_text="se compro un servicio?")
    inventario = models.BooleanField(default=False, help_text="la compra afectara el inventario?")
    precio = models.FloatField(null=True, default=0, blank=True, help_text="precio del rubro")
    subtotal = models.FloatField(null=True, default=0, blank=True, help_text="subtotal del rubro")
    history = HistoricalRecords()

class NotaCompra(Nota):
    compra = models.ForeignKey(Compra, null=False, blank=False, on_delete=models.DO_NOTHING, help_text="subtotal del rubro")
    history = HistoricalRecords()
