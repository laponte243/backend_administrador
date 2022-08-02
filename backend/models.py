
# Importes de Django
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import *
# Utiles
from simple_history.models import HistoricalRecords
""" Modelos del backend (api)"""
class Modulo(models.Model):
    nombre=models.TextField(max_length=20,blank=False,null=False)
    history=HistoricalRecords()
    def __str__(self):
        return '%s'%(self.nombre)
class Menu(models.Model):
    router=models.CharField(max_length=150,unique=True,blank=False,null=False,help_text="Nombre la opcion de menú")
    parent=models.ForeignKey('self',null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Si el menu es hijo de otro")
    orden=models.IntegerField(null=False,default=0)
    modulos=models.ForeignKey(Modulo,null=True,on_delete=models.DO_NOTHING)
    history=HistoricalRecords()
    def __str__(self):
        return '%s'%(self.router)
class Instancia(models.Model):
    nombre=models.TextField(max_length=150,blank=False,null=False,help_text="Nombre de la instancia")
    activo=models.BooleanField(default=True,help_text="esta la instancia activa?")
    multiempresa=models.BooleanField(default=True,help_text="esta la instancia es multiempresa?")
    vencimiento=models.DateTimeField(null=True,blank=False,help_text="Fecha de vencimiento de la instancia")
    modulos=models.ManyToManyField(Modulo,blank=False)
    history=HistoricalRecords()
    def __str__(self):
        return '%s'%(self.nombre)
    # def delete(self):
    #     self.activo=False
    #     self.save()
class MenuInstancia(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    menu=models.ForeignKey(Menu,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="SuperMenu asociado")   
    parent=models.ForeignKey('self',null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Si el menu es hijo de otro")
    orden=models.IntegerField(null=False,default=0)
    history=HistoricalRecords()
    def __str__(self):
        return '%s (MenuInstancia)'%(self.menu.router)
class Perfil(models.Model):
    TIPO=(('S','Super'),('A','Admin'),('U','Usuario'),('V','Vendedor'))
    instancia=models.ForeignKey(Instancia,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    usuario=models.OneToOneField(User,on_delete=models.CASCADE,help_text="usuario asociado")
    activo=models.BooleanField(default=True,help_text="esta el usuario activo?")
    avatar=models.ImageField(upload_to='avatars',null=True,help_text="avatar para el usuario")
    tipo=models.CharField(max_length=1,null=True,choices=TIPO,default='U',help_text="Tipo de usuario")
    history=HistoricalRecords()
    def __str__(self):
        return '%s - %s - %s'%(self.instancia.nombre,self.usuario.username,self.tipo)

# class ListaPrecios(models.Model):
#     instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
#     perfil = models.ForeignKey(Perfil,null=False,blank=False,on_delete=models.CASCADE,help_text="Usuario asociado")
#     marca_nombre=models.BooleanField(default=True)
#     marca_codigo=models.BooleanField(default=True)
#     descripcion_producto=models.BooleanField(default=True)
#     multi_precio=models.BooleanField(default=False)
#     iva=models.BooleanField(default=True)
#     precios=models.TextField(default=False)
#     history=HistoricalRecords()
#     def __str__(self):
#         return '%s - %s - %s'%(self.marca_nombre,self.marca_codigo,self.descripcion_producto)
class Permiso(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    menuinstancia=models.ForeignKey(MenuInstancia,null=False,blank=False,on_delete=models.CASCADE,help_text="Opcion de menu asociada")
    perfil=models.ForeignKey(Perfil,null=False,blank=False,on_delete=models.CASCADE,help_text="Usuario asociado")
    # Metodos
    leer=models.BooleanField(default=False,help_text="Tiene opcion de leer?")
    escribir=models.BooleanField(default=False,help_text="Tiene opcion de escribir?")
    borrar=models.BooleanField(default=False,help_text="Tiene opcion de borrar?")
    actualizar=models.BooleanField(default=False,help_text="Tiene opcion de actualizar?")
    # Utiles
    history=HistoricalRecords()
    # def save(self):
    #     if not Permiso.objects.filter(instancia=self.instancia_id,perfil=self.perfil_id,menuinstancia=self.menuinstancia_id):
    #         super().save()
    def __str__(self):
        return 'Permiso: %s - Leer:%s Borrar:%s Actualizar:%s Escribir:%s'%(self.menuinstancia.menu.router,self.leer,self.borrar,self.actualizar,self.escribir)
class Nota(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    TIPO=(('C','Credito'),('D','Debito'))
    subtotal=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="subtotal de la nota")
    descripcion=models.TextField(max_length=150,blank=False,null=True,help_text="descripcion del caso de la nota")
    tipo=models.CharField(max_length=1,choices=TIPO,default='C',help_text="que tipo de nota es")
    fecha=models.DateTimeField(auto_now_add=True,help_text="fecha de la nota")
    class Meta:
        abstract=True
class Empresa(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    nombre=models.CharField(max_length=150,blank=False,null=False,help_text="Razon social de la empresa")
    correo=models.CharField(max_length=150,blank=False,null=False,help_text="Correo de la empresa")
    direccion=models.TextField(blank=False,null=False,help_text="Direccion fiscal de la empresa")
    telefono=models.CharField(max_length=32,null=False,help_text="Telefono de la empresa")
    factura_grande=models.BooleanField(default=False,help_text="Formato de factura")
    #logo=models.TextField(null=True,help_text="Logo de la empresa")
    logo=models.FileField(null=True)
    history=HistoricalRecords()
    def __str__(self):
        return '%s'%(self.nombre)
    def save(self):
        super().save()
        if self.id and not ConfiguracionPapeleria.objects.filter(id=self.id):
            tipos=[
                'A', # Nota Devolucion
                'B', # Nota Control
                'C', # Nota Credito
                'D', # Nota Debito
                'E', # Proforma
                'F', # Factura
                'N', # Nota pago
                'P', # Pedido
            ]
            for p in tipos:
                correlativo=ConfiguracionPapeleria.objects.create(instancia=self.instancia,empresa=self,prefijo=None,valor=1,tipo=p)
                if p == 'E' or p == 'P' or p == 'F' or p == 'N':
                    correlativo.prefijo=p
                    correlativo.save()
class ContactoEmpresa(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    empresa=models.ForeignKey(Empresa,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="empresa asociada")
    nombre=models.TextField(max_length=150,blank=False,null=False,help_text="nombre del contacto")
    telefono=models.TextField(max_length=150,blank=False,null=False,help_text="telefono del contacto")
    mail=models.TextField(max_length=150,blank=False,null=False,help_text="correo electronico del contacto")
    history=HistoricalRecords()
    def __str__(self):
        return 'Contacto de la empresa %s'%(self.empresa)
class ConfiguracionPapeleria(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    TIPO=(('A','Nota devolucion'),('B','Nota Control'),('C','Nota credito'),('D','Nota debito'),('E','Proforma'),('F','Factura'),('N','Nota pago'),('P','Pedido'))
    empresa=models.ForeignKey(Empresa,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="empresa asociada")
    prefijo=models.TextField(max_length=10,blank=True,null=True,help_text="prefijo para el numero")
    formato=models.TextField(max_length=20,blank=True,null=True,help_text="formato de numero con 0 adelante 0000000")
    valor=models.IntegerField(blank=False,null=False,help_text="valor actual del numero")
    tipo=models.CharField(max_length=1,choices=TIPO,default='P',help_text="tipo de numero")
    history=HistoricalRecords()
    def __str__(self):
        return '%s, Empresa: %s, Siguiente: %s, Prefijo: %s'%(self.tipo,self.empresa,self.valor,self.prefijo)
class TasaConversion(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    fecha_tasa=models.DateTimeField(auto_now_add=True,help_text="tasa de conversion del dia")
    valor=models.DecimalField(max_digits=14,decimal_places=6,default=Decimal(0.0),null=False,help_text="valor de la tasa de conversion")
    history=HistoricalRecords()
    def __str__(self):
        return '%s (%s)'%(self.valor,self.fecha_tasa)
class Impuestos(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    nombre=models.TextField(max_length=30,blank=False,null=False,help_text="Nombre del impuesto")
    producto=models.BooleanField(default=False,help_text="afecta a solo ciertos productos?")
    activo=models.BooleanField(default=False,help_text="esta activo?")
    modificador=models.DecimalField(max_digits=5,decimal_places=2,default=Decimal(0.0),null=False,help_text="Cual es el porcentaje modificador de subtotal")
    regla=models.BooleanField(default=False,help_text="tiene una regla?")
    min=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Cual es el valor minimo en subtotal")
    max=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="cual es el valor maximo en subtotal")
    history=HistoricalRecords()
    def __str__(self):
        return '%s'%(self.nombre)
class Marca(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    nombre=models.TextField(max_length=220,blank=True,help_text="Nombre de la marca")
    prioridad=models.IntegerField(null=True,default=2)
    # logo=models.ImageField(upload_to='marcas',null=True,help_text="logo de la marca")
    history=HistoricalRecords()
    def __str__(self):
        return "%s [%s]"%(self.nombre,self.prioridad)
class Producto(models.Model):
    # Datos basicos
    instancia=models.ForeignKey(Instancia,null=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    # unidad=models.ForeignKey(Unidad,null=True,default= None,on_delete=models.DO_NOTHING,help_text="Unidad de medida del producto")
    marca=models.ForeignKey(Marca,null=False,on_delete=models.DO_NOTHING,help_text="Marca asociada al producto")
    nombre=models.TextField(max_length=150,null=False,blank=True,help_text="Nombre del producto")
    sku=models.TextField(max_length=150,null=False,blank=False,help_text="SKU del producto")
    servicio=models.BooleanField(default=False,help_text="¿Es un servicio?")
    MovimientoInventario_producto=models.BooleanField(default=False,help_text="¿Esta en un MovimientoInventario?")
    # Datos financieros
    costo=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Costo del producto")
    precio_1=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Precio del producto 1")
    precio_2=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Precio del producto 2")
    precio_3=models.DecimalField(max_digits=10,decimal_places=2,default=None,null=True,help_text="Precio del producto 3")
    precio_4=models.DecimalField(max_digits=10,decimal_places=2,default=None,null=True,help_text="Precio del producto 3")
    exonerado=models.BooleanField(default=False,help_text="¿Esta exonerado el impuesto?")
    # Datos configuracion
    venta_sin_inventario=models.BooleanField(default=False,help_text="¿Se permite la venta del producto sin inventario?")
    lote=models.BooleanField(default=False,help_text="¿Viene en lote?")
    activo=models.BooleanField(default=True,help_text="¿El producto esta activo?")
    menejo_inventario=models.BooleanField(default=True,help_text="¿Se manejara inventario del producto?")
    venta=models.BooleanField(default=True,help_text="¿Es un producto que se puede vender?")
    history=HistoricalRecords()
    def __str__(self):
        return self.nombre
class ProductoImagen(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    producto=models.ForeignKey(Producto,null=True,on_delete=models.DO_NOTHING,help_text="Producto asociado")
    imagen=models.ImageField(upload_to='productos',help_text="Imagen del producto")
    principal=models.BooleanField(default=False,help_text="Es la imagen principal del producto?")
    history=HistoricalRecords()
    def __str__(self):
        return 'Imagen de %s'%(self.producto)
class Almacen(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    nombre=models.TextField(max_length=220,blank=True,help_text="Nombre del almacen")
    activo=models.BooleanField(default=False,help_text="El almacen esta activo?")
    history=HistoricalRecords()
    def __str__(self):
        return self.nombre
class Inventario(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    producto=models.ForeignKey(Producto,null=False,on_delete=models.DO_NOTHING,help_text="producto asociado")
    almacen=models.ForeignKey(Almacen,null=True,on_delete=models.DO_NOTHING,help_text="almacen asociado")
    lote=models.TextField(null=False,blank=False,help_text="Numero de lote del producto")
    fecha_vencimiento=models.DateTimeField(null=True,blank=True,help_text="Fecha de vencimiento del producto")
    disponible=models.IntegerField(default=0,help_text="cantidad disponible")
    transito=models.IntegerField(default=0,help_text="cantidad en transito")
    bloqueado=models.IntegerField(default=0,help_text="cantidad bloqueada")
    min=models.IntegerField(null=True,default=None,help_text="Cantidad minima")
    max=models.IntegerField(null=True,default=None,help_text="Cantidad maxima")
    history=HistoricalRecords()
    def __str__(self):
        return "%s - %s - %s"%(self.producto,self.almacen,self.disponible)
class MovimientoInventario(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    inventario=models.ForeignKey(Inventario,null=False,on_delete=models.DO_NOTHING)
    producto=models.ForeignKey(Producto,null=False,on_delete=models.DO_NOTHING,help_text="Producto base del Movimiento Inventario")
    almacen=models.ForeignKey(Almacen,null=False,on_delete=models.DO_NOTHING,help_text="Almacen asociado")
    lote=models.TextField(null=True,blank=True,help_text="Numero de lote del producto")
    fecha_vencimiento=models.DateTimeField(null=True,blank=True,help_text="Fecha de vencimiento del producto")
    cantidad=models.IntegerField(default=0,null=False,help_text="Cantidad de recepcion del producto")
    descripcion=models.TextField(null=True,blank=True,help_text="Descripción del movimiento")
    TIPO=(('S','Salida'),('E','Entrada'))
    tipo=models.CharField(max_length=1,null=False,choices=TIPO,default='E',help_text="Tipo de usuario")
    history=HistoricalRecords() # colocar como registro
    def __str__(self):
        return "%s - %s - %s"%(self.producto,self.almacen,self.cantidad)
class Vendedor(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    nombre=models.TextField(max_length=150,blank=True,help_text="nombre completo del vendedor")
    identificador=models.TextField(max_length=150,blank=True,help_text="nombre completo del vendedor")
    telefono=models.TextField(max_length=150,blank=True,help_text="telefono del vendedor")
    correo=models.TextField(max_length=150,blank=True,help_text="correo asociado al vendedor")
    codigo=models.TextField(null=False,blank=False,help_text="codigo del vendedor")
    activo=models.BooleanField(default=False,help_text="Esta activo?")
    history=HistoricalRecords()
    def __str__(self):
        return 'Vendedor %s'%(self.nombre)
class Cliente(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    empresa=models.ForeignKey(Empresa,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="empresa asociada")
    vendedor=models.ForeignKey(Vendedor,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="vendedor asociado")
    nombre=models.TextField(max_length=150,blank=True,help_text="Razon social del cliente")
    telefono=models.TextField(max_length=150,blank=False,null=False,help_text="telefono del contacto")
    mail=models.TextField(max_length=150,blank=False,null=False,help_text="correo electronico del contacto")
    identificador=models.TextField(max_length=150,blank=True,help_text="Numero de indentificacion fiscal")
    ubicacion=models.TextField(max_length=150,blank=True,help_text="Ubicacion o direccion del cliente")
    credito=models.BooleanField(default=False,help_text="Se le puede vender a credito?")
    codigo=models.TextField(max_length=150,null=False,blank=False,help_text="Codigo del cliente")
    imagen=models.ImageField(upload_to='clientes',null=True,help_text="Imagen o logo asociado al cliente")
    activo=models.BooleanField(default=False,help_text="Esta activo?")
    history=HistoricalRecords()
    def __str__(self):
        return 'Cliente %s'%(self.nombre)
class ContactoCliente(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    cliente=models.ForeignKey(Cliente,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Cliente asociado")
    nombre=models.TextField(max_length=150,blank=False,null=False,help_text="Nombre del contacto")
    telefono=models.TextField(max_length=150,blank=False,null=False,help_text="telefono del contacto")
    mail=models.TextField(max_length=150,blank=False,null=False,help_text="correo electronico del contacto")
    history=HistoricalRecords()
    def __str__(self):
        return 'Contacto del cliente %s'%(self.cliente)
class Pedido(models.Model):
    ESTATUS=(('R','Revision'),('A','Aprobada'),('C','Cancelada'))
    estatus=models.CharField(max_length=1,default='R',choices=ESTATUS)
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    empresa=models.ForeignKey(Empresa,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="empresa asociada")
    cliente=models.ForeignKey(Cliente,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="cliente asociado")
    vendedor=models.ForeignKey(Vendedor,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="vendedor asociado")
    fecha_pedido=models.DateTimeField(auto_now_add=True,help_text="fecha de generacion del pedido")
    total=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="total de la pedido")
    precio_seleccionadoo=models.TextField(null= False,blank=False)
    numerologia=models.TextField(null=False,blank=True)
    history=HistoricalRecords()
    def __str__(self):
        return "ID: #%s,$%s (%s/%s)"%(self.id,self.total,self.cliente.nombre,self.empresa.nombre)
class DetallePedido(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    pedido=models.ForeignKey(Pedido,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Pedido asociado")
    precio_seleccionado=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=True)
    producto=models.ForeignKey(Producto,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Producto asociado")
    lote=models.TextField(max_length=150,blank=False,null=True,help_text="lote del producto")
    cantidada=models.IntegerField(default=0,null=False,help_text="Cantidad vendida")
    total_producto=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="total por producto")
    inventario=models.ForeignKey(Inventario,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Inventario asociado")
    history=HistoricalRecords()
    def __str__(self):
        return "Pedido: #%s,$%s (%s/%s)"%(self.pedido.id,self.total_producto,self.producto,self.lote)
class Proforma(models.Model):
    # impreso=models.BooleanField(default=False,help_text="Esta impreso?")
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    pedido=models.ForeignKey(Pedido,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="pedido asociado")
    empresa=models.ForeignKey(Empresa,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="empresa asociada")
    cliente=models.ForeignKey(Cliente,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="cliente asociado")
    vendedor=models.ForeignKey(Vendedor,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="vendedor asociado")
    # Datos
    precio_seleccionadoo=models.TextField(null= False,blank=False)
    nombre_cliente=models.TextField(max_length=150,blank=False,null=False,help_text="Nombre del cliente en la proforma")
    identificador_fiscal=models.TextField(max_length=150,blank=False,null=False,help_text="Identificador fiscal del cliente en la venta")
    direccion_cliente=models.TextField(max_length=150,blank=True,null=True,help_text="telefono del cliente en la proforma")
    telefono_cliente=models.TextField(max_length=150,blank=False,null=False,help_text="fecha de generacion de la proforma")
    saldo_proforma=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="saldo pendiente de la proforma")
    total=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="total de la proforma")
    total_iva=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="total de la proforma")
    fecha_proforma=models.DateTimeField(auto_now_add=True,help_text="fecha de generacion del pedido")
    numerologia=models.TextField(null=False,blank=True)
    fecha_despacho=models.DateTimeField(null=True,blank=True,default=None)
    # Utiles
    history=HistoricalRecords()
    def __str__(self):
        return "ID: #%s,$%s (%s/%s)"%(self.id,self.total,self.cliente.nombre,self.empresa.nombre)
class DetalleProforma(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    proforma=models.ForeignKey(Proforma,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="proforma asociada")
    precio_seleccionado=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False)
    producto=models.ForeignKey(Producto,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="detallepedido asociada")
    lote=models.TextField(max_length=150,blank=False,null=True,help_text="lote del producto")
    cantidada=models.IntegerField(null=False,default=0,blank=False,help_text="Cantidad vendida")
    descripcion=models.TextField(max_length=150,blank=False,null=True,help_text="En caso de no tener un producto asociado se puede colocar una descripcion del rublo acá")
    precio=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="precio del producto o servicio a vender")
    total_producto=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Precio por la cantidad del producto")
    inventario=models.ForeignKey(Inventario,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Inventario asociado")
    history=HistoricalRecords()
    def __str__(self):
        return "Proforma: #%s,$%s (%s/%s)"%(self.proforma.id,self.total_producto,self.producto,self.lote)
class NotaDevolucion(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    proforma=models.ForeignKey(Proforma,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Pedido asociado")
    empresa=models.ForeignKey(Empresa,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Empresa asociada")
    cliente=models.ForeignKey(Cliente,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Cliente asociado")
    vendedor=models.ForeignKey(Vendedor,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Vendedor asociado")
    # Datos
    precio_seleccionadoo=models.TextField(null= False,blank=False)
    nombre_cliente=models.TextField(max_length=150,blank=False,null=False,help_text="Nombre del cliente de la proforma")
    identificador_fiscal=models.TextField(max_length=150,blank=False,null=False,help_text="Identificador fiscal del cliente de la proforma")
    direccion_cliente=models.TextField(max_length=150,blank=True,null=True,help_text="Direccion del cliente de la proforma")
    telefono_cliente=models.TextField(max_length=150,blank=False,null=False,help_text="Telefono del cliente de la proforma")
    total=models.TextField(null=False,default=0,blank=False,help_text="Total de la devolucion")
    fecha_devolucion=models.TextField(help_text="Fecha de la devolucion")
    numerologia=models.TextField(null=False,blank=True)
    # Utiles
    history=HistoricalRecords()
    def __str__(self):
        return "ID: #%s,$%s (%s/%s)"%(self.id,self.total,self.cliente.nombre,self.empresa.nombre)

class DetalleNotaDevolucion(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    nota_devolucion=models.ForeignKey(NotaDevolucion,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Proforma asociada")
    producto=models.ForeignKey(Producto,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Producto asociado")
    inventario=models.ForeignKey(Inventario,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Inventario asociado")
    # Data
    precio_seleccionado=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False)
    lote=models.TextField(max_length=150,blank=False,null=True,help_text="Lote del producto")
    cantidada=models.IntegerField(null=False,default=0,blank=False,help_text="Cantidad devuelta")
    total_producto=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Precio por la cantidad del producto")
    # Extra
    history=HistoricalRecords()
    def __str__(self):
        return "NotaDevolucion: #%s,$%s (%s/%s)"%(self.nota_devolucion.id,self.total_producto,self.producto,self.lote)

class Factura(models.Model):
    # Llaves foraneas
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    proforma=models.ForeignKey(Proforma,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="proforma asociada")
    origen=models.IntegerField(null=True)
    # Cliente
    nombre_cliente=models.TextField(max_length=150,blank=False,null=False,help_text="Nombre del cliente en la venta")
    codigo_cliente=models.TextField(blank=False,null=False,help_text="Codigo del cliente asociado")
    identificador_fiscal=models.TextField(max_length=150,blank=False,null=False,help_text="Identificador fiscal del cliente en la venta")
    direccion_cliente=models.TextField(max_length=150,blank=False,null=False,help_text="telefono del cliente en la venta")
    telefono_cliente=models.TextField(max_length=150,null=False,blank=False,help_text="empresa asociada")
    correo_cliente=models.TextField(max_length=150,null=False,blank=False,help_text="empresa asociada")
    # Empresa
    nombre_empresa=models.TextField(max_length=150,null=False,blank=False,help_text="empresa asociada")
    telefonocontacto_empresa=models.TextField(max_length=150,null=False,blank=False,help_text="empresa asociada")
    direccion_empresa=models.TextField(max_length=150,null=False,blank=False,help_text="empresa asociada")
    formato_grande=models.BooleanField(default=False,help_text="empresa asociada")
    # Vendedor
    nombre_vendedor=models.TextField(max_length=150,null=True,blank=False,help_text="Nombre del vendedor asociado")
    codigo_vendedor=models.TextField(blank=False,null=False,help_text="Codigo del vendedor asociado")
    telefono_vendedor=models.TextField(max_length=150,null=False,blank=False,help_text="Telefono del vendedor asociado")
    # Total
    subtotal=models.TextField(max_length=150,null=False,default=0,blank=False,help_text="subtotal de la venta")
    monto_exento=models.TextField(max_length=150,null=False,default=0,blank=False,help_text="monto exento de la proforma")
    impuesto=models.TextField(max_length=150,null=False,default=0,blank=False,help_text="monto exento de la proforma")
    total=models.TextField(max_length=150,null=False,default=0,blank=False,help_text="total de la venta")
    # Datos de pago
    tipo_pago=models.TextField(max_length=150,blank=False,null=False,help_text="tipo de pago utilizado por el cliente de la venta")
    credito=models.TextField(default=False,help_text="La venta se realizo a credito?")
    dias_credito=models.TextField(null=True,default=0,help_text="dias de credito?")
    # Utiles
    # impreso=models.BooleanField(default=False,help_text="Esta impreso?")
    pdf=models.FileField(upload_to='facturacion/pdfs',null=True)
    fecha_factura=models.DateTimeField(auto_now_add=True,help_text="fecha de generacion del pedido")
    numerologia=models.TextField(null=False,blank=False)
    control=models.TextField(null=False,blank=False)
    history=HistoricalRecords()
    def save(self):
        if self.id and not self.origen:
            self.origen = self.proforma.id
        super().save()
    def __str__(self):
        return "Factura: #%s (%s),$%s (%s/%s)"%(self.id,self.proforma.id if self.proforma else 'Nulificado',self.total,self.nombre_cliente,self.nombre_empresa)
class DetalleFactura(models.Model):
    # Relaciones foraneas principales
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    factura=models.ForeignKey(Factura,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Factura asociada")
    # Producto
    producto=models.ForeignKey(Producto,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Producto asociada")
    inventario=models.ForeignKey(Inventario,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="Inventario asociado")
    producto_fijo=models.TextField(max_length=150,null=False,blank=False,help_text="Producto asociado fijado")
    inventario_fijo=models.TextField(max_length=150,null=True,blank=False,help_text="Inventario asociado fijado")
    lote=models.TextField(max_length=150,blank=False,null=True,help_text="Lote del producto fijado")
    cantidada=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Cantidad vendida")
    precio=models.TextField(max_length=150,null=False,default=0,blank=False,help_text="Precio del producto o servicio a vender fijado")
    # Total del detalle
    total_producto=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Total final del detalle")
    # Utiles
    descripcion=models.TextField(max_length=150,blank=False,null=True,help_text="En caso de no tener un producto asociado se puede colocar una descripcion del rublo aca")
    fecha_vencimiento=models.TextField(max_length=150,null=True,blank=False,help_text="Fecha de vencimiento del MovimientoInventario")
    history=HistoricalRecords()
    def __str__(self):
        return "Factura: #%s,$%s (%s/%s)"%(self.factura.id,self.total_producto,self.producto,self.lote)
class ImpuestosFactura(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    factura=models.ForeignKey(Factura,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="venta asociada")
    nombre=models.TextField(max_length=100,blank=False,null=True,help_text="nombre del impuesto asociado")
    subtotal=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="subtotal del impuesto asociado a la venta")
    history=HistoricalRecords()
    def __str__(self):
        return 'Impuesto dado a %s'%(self.factura)
class NumerologiaFactura(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    factura=models.ForeignKey(Factura,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Venta asociada")
    tipo=models.TextField(max_length=100,blank=False,null=True,help_text="Tipo de numerologia")
    valor=models.TextField(max_length=100,blank=False,null=True,help_text="valor que se utilizo en la venta")
    history=HistoricalRecords()
class NotaFactura(Nota):
    factura=models.ForeignKey(Factura,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="venta asociada")
    history=HistoricalRecords()
    def __str__(self):
        return 'Nota asociada a "%s"'%(self.factura)
class NotasPago(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    cliente=models.ForeignKey(Cliente,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="cliente asociado")
    vendedor=models.ForeignKey(Vendedor,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Vendedor asociado")
    total=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="Total de la nota")
    comprobante=models.TextField(null=False,default=0,blank=False,help_text="Comprobante de la nota de pago")
    fecha_comprobante=models.DateTimeField(null=False,blank=False,help_text="Fecha del comprobante")
    descripcion=models.TextField(max_length=150,blank=True,null=True,help_text="Pequeña descripcion")
    numerologia=models.TextField(null=False,blank=True)
    fecha=models.DateTimeField(auto_now_add=True)
class DetalleNotasPago(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    notapago=models.ForeignKey(NotasPago,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="nota de pago asociada")
    proforma=models.ForeignKey(Proforma,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="proforma a la que afecta")
    saldo_anterior=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="saldo anterior de la proforma")
    monto=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="monto a descontar")
#Compras
class Proveedor(models.Model):
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    empresa=models.ForeignKey(Empresa,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="empresa asociada")
    marcas=models.ManyToManyField(Marca,help_text="marcas asociadas")
    nombre=models.TextField(max_length=150,blank=True,help_text="nombre del proveedor")
    identificador=models.TextField(max_length=150,blank=True,help_text="identificador fiscal asociado")
    ubicacion=models.TextField(max_length=150,blank=True,help_text="Ubicacion del proveedor")
    credito=models.BooleanField(default=False,help_text="el proveedor da credito?")
    imagen=models.ImageField(upload_to='proveedores',null=True,help_text="imagen asociada al proveedor")
    history=HistoricalRecords()
    def __str__(self):
        return 'Proveedor %s'%(self.nombre)
class Compra(models.Model):
    # Relaciones foraneas
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    empresa=models.ForeignKey(Empresa,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="empresa asociada")
    Proveedor=models.ForeignKey(Cliente,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="proveedor asoaciado")
    # Factura de compra
    fecha_factura=models.DateTimeField(auto_now_add=True,help_text="fecha de la factura de compra")
    numero_factura=models.TextField(max_length=150,blank=False,null=False,help_text="numero de la factura")
    numero_control=models.TextField(max_length=150,blank=False,null=True,help_text="numero de control")
    # Datos pago
    tipo_pago=models.TextField(max_length=150,blank=False,null=False,help_text="tipo de pago utilizado")
    credito=models.BooleanField(default=False,help_text="la factura es a credito?")
    dias_credito=models.IntegerField(null=True,default=0,help_text="cuantos dias de credito?")
    # Total
    subtotal=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="subtotal de la factura")
    impuestos=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="total en impuestos")
    total=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="total en factura")
    # Utiles
    history=HistoricalRecords()
    def __str__(self):
        return 'Compra: %s'%(self.factura)
class DetalleCompra(models.Model):
    # Relaciones foraneas
    instancia=models.ForeignKey(Instancia,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
    compra=models.ForeignKey(Compra,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="compra asociada")
    # Producto
    producto=models.ForeignKey(Producto,null=True,blank=False,on_delete=models.DO_NOTHING,help_text="producto asociado")
    inventario=models.BooleanField(default=False,help_text="la compra afectara el inventario?")
    cantidad=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="cantidad comprada")
    servicio=models.BooleanField(default=False,help_text="se compro un servicio?")
    # Total
    precio=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="precio del rubro")
    subtotal=models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.0),null=False,help_text="subtotal del rubro")
    # Utiles
    descripcion=models.TextField(max_length=150,blank=False,null=True,help_text="En caso de no tener producto asociado a la compra se puede colocar una descripcion del rubro")
    history=HistoricalRecords()
    def __str__(self):
        return "Factura: #%s,$%s (%s/%s)"%(self.factura.id,self.total_producto,self.producto,self.lote)
class NotaCompra(Nota):
    compra=models.ForeignKey(Compra,null=False,blank=False,on_delete=models.DO_NOTHING,help_text="subtotal del rubro")
    history=HistoricalRecords()
    def __str__(self):
        return 'Nota asociada a %s'%(self.compra)