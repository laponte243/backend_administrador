# Importes de Rest framework
from struct import pack
from rest_framework import permissions,viewsets,status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authtoken.models import Token
from rest_framework.authentication import SessionAuthentication,BasicAuthentication,TokenAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.permissions import IsAdminUser,IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework.utils import json
from django_filters.rest_framework import DjangoFilterBackend
# Importes de Django
from django.apps import apps
from django.db.models import *
from django.contrib.auth import *
from django.core import serializers as sr
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse,HttpResponse,request,QueryDict
from django.shortcuts import render,get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
# Raiz
from .serializers import *
from .models import *
from .menu import *
from . import views
from .utils import render_to_pdf
# from .vistas import *
# Recuperar contraseña
from knox.views import LoginView as KnoxLoginView
from django.conf import settings
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.core.files import File
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.template.loader import render_to_string
# Utiles
from django_renderpdf.views import PDFView
from email import header
from urllib import response
from numpy import indices, safe_eval
from io import BytesIO
from decimal import *
from xlwt import *
import pandas as pd
import csv
import requests
import datetime
import random
import string


# Notas de devolucion registradas en la instancia
class NotaDevolucionVS(viewsets.ModelViewSet):
    # Permisos
    permiso='NotaDevolucion'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=NotaDevolucion
    queryset=modelo.objects.all()
    serializer_class=NotaDevolucionSerializer
    # Metodo crear
    def create(self,request):
        perfil=views.obt_per(self.request.user)
        if views.verificar_permiso(perfil,'NotaDevolucion','escribir'):
            datos=request.data
            try:
                datos['instancia']=views.obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia']=perfil.instancia.id
            datos['fecha_devolucion'] = timezone.now().date()
            configuracion=views.verificar_numerologia(datos,self.modelo)
            datos['numerologia']=configuracion.valor
            serializer=self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers=self.get_success_headers(serializer.data)
            configuracion.valor+=1
            configuracion.save()
            for d in datos['detalles']:
                detalle = DetalleNotaDevolucion.objects.create(
                    instancia=perfil.instancia,
                    nota_devolucion=serializer.data.id,
                    producto=d['producto'],
                    inventario=d['inventario'],
                    precio_seleccionado=d['precio_seleccionado'],
                    lote=d['lote'],
                    cantidada=d['cantidada'],
                    total_producto=d['total_producto'],
                )
                #NotaDevolucion
                views.modificar_inventario('devolver',detalle.inventario,detalle.cantidada)
            return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil=views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','actualizar'):
        #     partial=True
        #     instance=self.get_object()
        #     try:
        #         if request.data['fecha_despacho'] == True and instance.fecha_despacho == None:
        #             request.data['fecha_despacho'] = timezone.now()
        #     except Exception as e:
        #         print(e)
        #     if instance.instancia==perfil.instancia or perfil.tipo=='S':
        #         serializer=self.get_serializer(instance,data=request.data,partial=partial)
        #         serializer.is_valid(raise_exception=True)
        #         self.perform_update(serializer)
        #         return Response(serializer.data,status=status.HTTP_200_OK)
        #     else:
        #         return Response(status=status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil=views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','borrar'):
        #     instance=self.get_object()
        #     if instance.instancia==perfil.instancia or perfil.tipo=='S':
        #         DetalleNotaDevolucion.objects.filter(nota_devolucion=instance.id).delete()
        #         instance.delete()
        #         return Response(status=status.HTTP_204_NO_CONTENT)
        #     else:
        #         return Response(status=status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodos de leer
    def list(self,request):
        try:
            perfil=views.obt_per(self.request.user)
            if views.verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=views.paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if views.verificar_permiso(views.obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)

# Detalles de las notas de devolucion de la instancia
class DetalleNotaDevolucionVS(viewsets.ModelViewSet):
    # Permisos
    permiso='NotaDevolucion'
    permission_classes=[IsAuthenticated]
    authentication_classes=[TokenAuthentication]
    # Datos
    modelo=DetalleNotaDevolucion
    queryset=modelo.objects.all()
    serializer_class=DetalleNotaDevolucionSerializer
    # Metodo crear
    def create(self,request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil=views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','escribir'):
        #     datos=request.data
        #     try:
        #         datos['instancia']=views.obtener_instancia(perfil,request.data['instancia'])
        #     except:
        #         datos['instancia']=perfil.instancia.id
        #     serializer=self.get_serializer(data=datos)
        #     serializer.is_valid(raise_exception=True)
        #     self.perform_create(serializer)
        #     headers=self.get_success_headers(serializer.data)
        #     return Response(serializer.data,status=status.HTTP_201_CREATED,headers=headers)
        # else:
        #     return Response(status=status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil=views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','actualizar'):
        #     partial=True
        #     instance=self.get_object()
        #     if instance.instancia==perfil.instancia or perfil.tipo=='S':
        #         serializer=self.get_serializer(instance,data=request.data,partial=partial)
        #         serializer.is_valid(raise_exception=True)
        #         self.perform_update(serializer)
        #         return Response(serializer.data,status=status.HTTP_200_OK)
        #     else:
        #         return Response(status=status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status=status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil=views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','borrar'):
        #     instance=self.get_object()
        #     inventario=Inventario.objects.get(id=instance.inventario.id)
        #     inventario.disponible=inventario.disponible+instance.cantidada
        #     if instance.instancia==perfil.instancia or perfil.tipo=='S':
        #         instance.delete()
        #         inventario.save()
        #         return Response(status=status.HTTP_204_NO_CONTENT)
        #     else:
        #         return Response(status=status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Metodos de leer
    def list(self,request):
        try:
            perfil=views.obt_per(self.request.user)
            if views.verificar_permiso(perfil,self.permiso,'leer'):
                instancia=perfil.instancia
                # Filtrar los objetos
                objetos=self.queryset if perfil.tipo=='S' else self.queryset.filter(perfil__instancia=instancia)
                objetos=objetos.exclude(perfil__tipo__in=['A','S']) if perfil.tipo=='U' or perfil.tipo=='V' else objetos
                # Paginacion
                paginado=views.paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data=self.serializer_class(paginado['objetos'],many=True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status=status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk=None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk=pk)).data) if views.verificar_permiso(views.obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_401_UNAUTHORIZED)













@api_view(["POST"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def guardar_configuracion_lista_precio(request):
    data = request.data
    try:
        i = 0
        for marca in Marca.objects.all():
            marca.prioridad
            if marca.id in data['marcas']:
                i += 1
                marca.prioridad = i
            marca.save()
        return Response('Guardado',status=status.HTTP_200_OK)
    except Exception as e:
        print(data)
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def generar_lista_precio(request):
    params=request.query_params.copy()
    token=params.get('token').split(' ')[1]
    if Token.objects.get(key=token):
        perfil=Perfil.objects.get(usuario=1)
        if views.verificar_permiso(perfil,'Productos','leer'):
            # Crear archivo temporal
            response=HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition']='attachment;filename="lista_precios.xls"'
            # Iniciar Excel
            excel_wb=Workbook(encoding='utf-8')
            excel_ws=excel_wb.add_sheet('Hoja1') # ws es Work Sheet
            # Añadiendo estilo
            # excel_ws.col(0).width = 3500
            excel_ws.col(0).width = 16500 # Tamaño columna codigo producto
            excel_ws.col(1).width = 4900 # Tamaño columna marca producto
            excel_ws.col(2).width = 2600 # Tamaño columna precio producto
            excel_ws.col(3).width = 2000 # Tamaño columna iva producto
            # Color cabezera
            add_palette_colour("color_cabezera", 0x21)
            excel_wb.set_colour_RGB(0x21, 200, 200, 200)
            # Color nombre marca
            add_palette_colour("color_marca", 0x22)
            excel_wb.set_colour_RGB(0x22, 160, 160, 210)
            # Estilo cabezeras
            borders_a = 'borders:\
                            top_color black, top thin,\
                            right_color black, right thin,\
                            bottom_color black, bottom 1,\
                            left_color black, left thin;'
            estilo_cabezera = easyxf('font: bold 1, height 260;\
                                      align: wrap on, horiz center;\
                                      %s\
                                      pattern: pattern solid, fore_colour color_cabezera'%(borders_a))
            lefted = easyxf('align: wrap on, horiz left;%s'%(borders_a))
            centered = easyxf('align: wrap on, horiz center;%s'%(borders_a))
            righted = easyxf('align: wrap on, horiz right;%s'%(borders_a))
            estilo_nombre_marca = easyxf('font: bold 1, height 300; align: wrap on, horiz center; pattern: pattern solid, fore_colour color_marca')
            i=4 # Saltador de fila
            # Escribir nombres de las columnas
            ahora = datetime.datetime.now()
            estilo_dia = easyxf('font: bold 1, height 300; align: wrap on, horiz center')
            celdas_nombre_marca = []
            excel_ws.write(i,0,'LISTA DE PRECIOS AL: %s/%s/%s'%(ahora.day,ahora.month,ahora.year),estilo_dia)
            celdas_nombre_marca.append(i)
            i=i+2 # Saltador de fila    
            excel_ws.write(i,0,'DESCRIPCIÓN',estilo_cabezera)
            excel_ws.write(i,1,'MARCA',estilo_cabezera)
            excel_ws.write(i,2,'PRECIO',estilo_cabezera)
            excel_ws.write(i,3,'IVA',estilo_cabezera)
            excel_ws.set_panes_frozen(True)
            excel_ws.set_horz_split_pos(7)
            # Ciclo por cada marca
            marcas_elegidas = params.get('marcas').split(',')
            for id_marca in marcas_elegidas if marcas_elegidas[0] != '0' else Marca.objects.all().values_list('id'):
                marca = Marca.objects.get(id=id_marca if type(id_marca) != type(()) else id_marca[0])
                i=i+2 # Saltar fila
                # Ciclo por cada producto
                excel_ws.write(i,0,marca.nombre,estilo_nombre_marca)
                celdas_nombre_marca.append(i)
                i=i+1 # Saltar fila
                for p in Producto.objects.filter(marca=marca).order_by('nombre').values():
                    i=i+1 # Saltar fila
                    # Escribir productos
                    # excel_ws.write(i,0,m['nombre']) # Nombre marca
                    # excel_ws.write(i,1,p['sku']) # Codigo producto
                    excel_ws.write(i,0,p['nombre'],lefted) # Nombre producto
                    excel_ws.write(i,1,marca.nombre,centered) # Nombre producto
                    precio = None
                    # Precios del producto
                    if params.get('precio') == 'precio_1':
                        precio = round(p['precio_1'],2)
                    elif params.get('precio') == 'precio_2':
                        precio = round(p['precio_2'],2)
                    elif params.get('precio') == 'precio_3':
                        precio = round(p['precio_3'],2)
                    elif params.get('precio') == 'precio_4':
                        precio = round(p['precio_4'],2)
                    extra_cero_precio = True if len(str(round(precio,2)).split('.')[1]) < 2 else False
                    excel_ws.write(i,2,'%s'%(precio) if not extra_cero_precio else '%s0'%(precio),righted)
                    if not p['exonerado']:
                        iva = Decimal(round(precio*(Decimal(16)/Decimal(100)),2))
                        extra_cero_iva = True if len(str(iva).split('.')[1]) < 2 else False
                        excel_ws.write(i,3,'%s'%(iva) if not extra_cero_iva else '%s0'%(iva),righted)
                    else:
                        excel_ws.write(i,3,'',righted)
            for row in range(i):
                excel_ws.row(row).height = 400 if row in celdas_nombre_marca else 320
            # Guardar excel en el archivo temporal
            excel_wb.save(response)
            # Restornar archivo
            return response
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
    return Response('',status=status.HTTP_501_NOT_IMPLEMENTED)

data_temporal = {'vendedor':0}

@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def analisis_vencimiento(request):
    params=request.query_params.copy()
    usuario = Token.objects.get(key=params.get('token').split(' ')[1]).user
    # if usuario:
    data = int(params.get('vendedor'))
    if not data:
        data=data_temporal['vendedor']
    perfil=Perfil.objects.get(usuario=1)
    if views.verificar_permiso(perfil,'Productos','leer'):
        response=HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition']='attachment;filename="analisis_vencimiento.xls"'
        # Iniciar Excel
        excel_wb=Workbook(encoding='utf-8')
        excel_ws=excel_wb.add_sheet('Hoja1') # ws es Work Sheet
        # Añadiendo estilo
        excel_ws.col(0).width = 2700 # Tamaño columna numero NotaDevolucion
        excel_ws.col(1).width = 3400 # Tamaño columna emision NotaDevolucion
        excel_ws.col(2).width = 3400 # Tamaño columna despacho NotaDevolucion
        excel_ws.col(3).width = 3900 # Tamaño columna monto total NotaDevolucion
        excel_ws.col(4).width = 3900 # Tamaño columna saldo NotaDevolucion
        excel_ws.col(5).width = 1500 # Tamaño columna dias Despacho/Hoy
        bold=easyxf('font: bold 1')
        center=easyxf('align: wrap on, horiz center')
        right=easyxf('align: wrap on, horiz right')
        vendedores = Vendedor.objects.filter(instancia=Perfil.objects.get(usuario=usuario).instancia)
        vendedores = vendedores.filter(id__exact=data) if data != 0 else vendedores
        ahora = timezone.now()
        i = 0
        excel_ws.write(i,0,'ANALISIS DE VENCIMIENTO CTAS x COBRAR al: %s'%(ahora.date()),bold)
        for vendedor in vendedores:
            proformas_vendedor = Proforma.objects.filter(vendedor=vendedor).exclude(saldo_proforma=Decimal(0.0))
            if proformas_vendedor:
                i += 2
                excel_ws.write(i,0,'VENDEDOR: %s, CODIGO: %s'%(vendedor.nombre,vendedor.codigo),bold)
                for cliente in Cliente.objects.filter(vendedor=vendedor):
                    proformas_cliente = proformas_vendedor.filter(cliente=cliente)
                    if proformas_cliente:
                        i += 1
                        excel_ws.write(i,0,'CLIENTE:',bold)
                        excel_ws.write(i,1,'%s %s'%(cliente.codigo,cliente.nombre),bold)
                        excel_ws.write(i,3,'RIF: %s'%(cliente.identificador),bold)
                        excel_ws.write(i,4,'Telf: %s'%(cliente.telefono),bold)
                        i += 1
                        excel_ws.write(i,0,'NotaDevolucion',bold)
                        excel_ws.write(i,1,'Fecha Emis',bold)
                        excel_ws.write(i,2,'Fecha Desp',bold)
                        excel_ws.write(i,3,'Monto Emis',bold)
                        excel_ws.write(i,4,'Saldo',bold)
                        excel_ws.write(i,5,'Dias',bold)
                        i += 1
                        total = 0
                        pendiente = 0
                        for proforma in proformas_cliente:
                            correlativo=ConfiguracionPapeleria.objects.get(empresa=proforma.empresa,tipo="E")
                            excel_ws.write(i,0,'%s%s'%(correlativo.prefijo+'-' if correlativo.prefijo else '',proforma.numerologia))
                            excel_ws.write(i,1,'%s'%(proforma.fecha_proforma.date()),center)
                            if proforma.fecha_despacho:
                                excel_ws.write(i,2,'%s'%(proforma.fecha_despacho.date()),center)
                                excel_ws.write(i,5,'%s'%((ahora.date() - proforma.fecha_despacho.date()).days),center)
                            else:
                                excel_ws.write(i,2,'Sin despachar')
                                excel_ws.write(i,5,'-',center)
                            total_proforma = str(round(proforma.total,2))
                            saldo_proforma = str(round(proforma.saldo_proforma,2))
                            if len(total_proforma.split('.')[1]) == 1: total_proforma = total_proforma + '0'
                            if len(saldo_proforma.split('.')[1]) == 1: saldo_proforma = saldo_proforma + '0'
                            excel_ws.write(i,3,'%s'%(total_proforma),right)
                            excel_ws.write(i,4,'%s'%(saldo_proforma),right)
                            total += round(proforma.total,2)
                            pendiente += round(proforma.saldo_proforma,2)
                            i += 1
                        excel_ws.write(i,1,'TOTAL CLIENTE %s:'%(cliente.codigo),bold)
                        excel_ws.write(i,3,'%s'%(round(total,2)),right)
                        excel_ws.write(i,4,'%s'%(round(pendiente,2)),right)
                        # i += 1
        # Guardado temporal del excel
        excel_wb.save(response)
        # Retornar y generar
        return response
    return Response('',status=status.HTTP_501_NOT_IMPLEMENTED)
    # else:
    #     return Response(status=status.HTTP_403_FORBIDDEN)


def crear_factura(context,kwargs):
    context['error'] = None
    try:
        if Token.objects.get(key=kwargs['token']):
            conversion=None
            try:
                conversion=TasaConversion.objects.filter(fecha_tasa__date=datetime.datetime.today().date()).first('fecha_tasa__date')
            except:
                conversion=TasaConversion.objects.latest('fecha_tasa')
            factura=Factura.objects.get(id=kwargs['id_factura'])
            subtotal=Decimal(float(factura.subtotal))
            total_costo=round(Decimal(float(factura.total)) * conversion.valor, 2)
            value={'data':[]}
            total_exento=0
            total_imponible=0
            total_calculado=0
            # Ciclo para generar Json y data para el template
            for dato in DetalleFactura.objects.filter(factura=factura).values('id', 'producto', 'precio').annotate(total=Sum('total_producto'), cantidad=Sum('cantidada')):
                productox=Producto.objects.get(id=dato['producto'])
                if productox.exonerado == False:
                    total_imponible +=dato['total']
                else:
                    total_exento +=dato['total']
                valuex={'datax':[]}
                total_cantidad=0
                precio_unidad=0.0
                costo_total=0.0
                mostrar=True
                detallado=DetalleFactura.objects.filter(factura=factura, producto=productox).order_by('producto__id')
                if productox.lote==True and len(detallado) > 1:
                    for detalle in detallado:
                        valuex['datax'].append({'lote':detalle.lote if detalle.lote else 'Sin lote', 'cantidad':detalle.cantidada, 'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''})
                        total_cantidad +=int(detalle.cantidada)
                        precio_unidad=Decimal(float(detalle.precio)) * conversion.valor
                elif productox.lote==True and len(detallado)==1:
                    valuex['datax']=''
                    mostrar=False
                    for detalle in detallado:
                        valuex['datax'] = {'lote':detalle.lote, 'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''}
                        total_cantidad +=int(detalle.cantidada)
                        precio_unidad=Decimal(float(detalle.precio)) * conversion.valor
                else:
                    mostrar=False
                    for detalle in detallado:
                        total_cantidad +=int(detalle.cantidada)
                        precio_unidad=Decimal(float(detalle.precio)) * conversion.valor
                    valuex['datax']=None
                costo_total=precio_unidad * Decimal(float(total_cantidad))
                total_calculado +=costo_total
                extra_cero_precio = True if len(str(round(precio_unidad, 2)).split('.')[1]) < 2 else False
                extra_cero_total = True if len(str(round(costo_total, 2)).split('.')[1]) < 2 else False
                value['data'].append({'producto_nombre':productox.nombre, 'extra_cero_precio':extra_cero_precio, 'extra_cero_total':extra_cero_total, 'exento':productox.exonerado, 'producto_sku':productox.sku, 'detalle':valuex['datax'], 'mostrar':mostrar, 'cantidad':total_cantidad, 'precio':round(precio_unidad, 2), 'total_producto':round(costo_total, 2)})
            subtotal_conversion=subtotal * conversion.valor
            # Sumatoria de los no exentos (Imponible)
            total_imponible = total_imponible * conversion.valor
            # Sumatoria de los exentos (Exonerados)
            total_exento = total_exento * conversion.valor
            total_real=(total_imponible + total_exento)
            # 16% (IVA)
            iva=round(total_imponible*Decimal(16/100), 2)
            if total_imponible:
                total_real=total_real + iva
            # Setear los valores al template
            context['productos']=value['data']
            context['subtotal']=round(subtotal_conversion, 2)
            context['extra_cero_subtotal'] = True if len(str(round(subtotal_conversion, 2)).split('.')[1]) < 2 else False
            context['imponible']=round(total_imponible, 2)
            context['extra_cero_imponible'] = True if len(str(round(total_imponible, 2)).split('.')[1]) < 2 else False
            context['monto_exento']=round(total_exento, 2)
            context['extra_cero_monto_exento'] = True if len(str(round(total_exento, 2)).split('.')[1]) < 2 else False
            context['impuesto']=iva
            context['extra_cero_impuesto'] = True if len(str(round(iva, 2)).split('.')[1]) < 2 else False
            context['total']=round(total_real, 2)
            context['extra_cero_total_real'] = True if len(str(round(total_real, 2)).split('.')[1]) < 2 else False
            context['factura']=factura
            context['correlativo_proforma']=factura.proforma.numerologia
            # Setear los valores de la empresa
            empresa=factura.proforma.cliente.empresa
            context['empresa']={'nombre':empresa.nombre.upper(), 'correo':empresa.correo, 'telefono':empresa.telefono, 'direccion':empresa.direccion}
            return context
        else:
            raise Exception('Token del usuario invalido')
    except Exception as e:
        print('error',e)
        context['error'] = e
        return context

# @api_view(["GET"])
# @csrf_exempt
# @authentication_classes([BasicAuthentication])
# @permission_classes([AllowAny])
# def generar_pdf_factura(request, *args, **kwargs):
#     context = {}
#     context['error'] = None
#     try:
#         if Token.objects.get(key=kwargs['token']):
#             # Obtener factura
#             factura = Factura.objects.get(id=kwargs['id_factura'])
#             # Obtener tasa conversion
#             conversion=None
#             try: conversion=TasaConversion.objects.filter(fecha_tasa__date=datetime.datetime.today().date()).first('fecha_tasa__date')
#             except: conversion=TasaConversion.objects.latest('fecha_tasa')
#             # Valores iniciales factura
#             subtotal=Decimal(float(factura.subtotal))
#             total_costo=round(Decimal(float(factura.total)) * conversion.valor, 2)
#             value={'data':[]}
#             total_exento=0
#             total_imponible=0
#             total_calculado=0
#             # Ciclo para generar Json y data para el template
#             for dato in DetalleFactura.objects.filter(factura=factura).values('id', 'producto', 'precio').annotate(total=Sum('total_producto'), cantidad=Sum('cantidada')):
#                 # Obtener producto del detalle
#                 productox=Producto.objects.get(id=dato['producto'])
#                 # Productos con IVA
#                 if productox.exonerado == False: total_imponible += dato['total']
#                 else: total_exento += dato['total']
#                 # Valores iniciales del detalle
#                 valuex={'datax':[]}
#                 total_cantidad=0
#                 precio_unidad=0.0
#                 costo_total=0.0
#                 mostrar=True
#                 # Obtener detalle
#                 detallado=DetalleFactura.objects.filter(factura=factura, producto=productox).order_by('producto__id')
#                 # Detalle con varios lotes visibles
#                 if productox.lote == True and len(detallado) > 1:
#                     for detalle in detallado:
#                         valuex['datax'].append({'lote':detalle.lote if detalle.lote else 'Sin lote', 'cantidad':detalle.cantidada, 'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''})
#                         total_cantidad +=int(detalle.cantidada)
#                         precio_unidad=Decimal(float(detalle.precio)) * conversion.valor
#                 # Detalle con un lote visible
#                 elif productox.lote==True and len(detallado)==1:
#                     valuex['datax']=''
#                     mostrar=False
#                     for detalle in detallado:
#                         valuex['datax'] = {'lote':detalle.lote, 'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''}
#                         total_cantidad +=int(detalle.cantidada)
#                         precio_unidad=Decimal(float(detalle.precio)) * conversion.valor
#                 # Detalle sin lote visible
#                 else:
#                     mostrar=False
#                     for detalle in detallado:
#                         total_cantidad +=int(detalle.cantidada)
#                         precio_unidad=Decimal(float(detalle.precio)) * conversion.valor
#                     valuex['datax']=None
#                 # Obtener costo total del detalle
#                 costo_total=precio_unidad * Decimal(float(total_cantidad))
#                 # Sumar costo toital al total calculado
#                 total_calculado += costo_total
#                 # Añadir cero en el template
#                 extra_cero_precio = True if len(str(round(precio_unidad, 2)).split('.')[1]) < 2 else False
#                 extra_cero_total = True if len(str(round(costo_total, 2)).split('.')[1]) < 2 else False
#                 # Agregar detalle al array del context
#                 value['data'].append({'producto_nombre':productox.nombre, 'extra_cero_precio':extra_cero_precio, 'extra_cero_total':extra_cero_total, 'exento':productox.exonerado, 'producto_sku':productox.sku, 'detalle':valuex['datax'], 'mostrar':mostrar, 'cantidad':total_cantidad, 'precio':round(precio_unidad, 2), 'total_producto':round(costo_total, 2)})
#             # Obtener sub total
#             subtotal_conversion=subtotal * conversion.valor
#             # Sumatoria de los no exentos (Imponible)
#             total_imponible = total_imponible * conversion.valor
#             # Sumatoria de los exentos (Exonerados)
#             total_exento = total_exento * conversion.valor
#             total_real=(total_imponible + total_exento)
#             # 16% (IVA)
#             iva=round(total_imponible*Decimal(16/100), 2)
#             if total_imponible:
#                 total_real=total_real + iva
#             # Setear los valores del template
#             context['productos']=value['data']
#             context['subtotal']=round(subtotal_conversion, 2)
#             context['extra_cero_subtotal'] = True if len(str(round(subtotal_conversion, 2)).split('.')[1]) < 2 else False
#             context['imponible']=round(total_imponible, 2)
#             context['extra_cero_imponible'] = True if len(str(round(total_imponible, 2)).split('.')[1]) < 2 else False
#             context['monto_exento']=round(total_exento, 2)
#             context['extra_cero_monto_exento'] = True if len(str(round(total_exento, 2)).split('.')[1]) < 2 else False
#             context['impuesto']=iva
#             context['extra_cero_impuesto'] = True if len(str(round(iva, 2)).split('.')[1]) < 2 else False
#             context['total']=round(total_real, 2)
#             context['extra_cero_total_real'] = True if len(str(round(total_real, 2)).split('.')[1]) < 2 else False
#             context['factura']=factura
#             context['correlativo_proforma']=factura.proforma.numerologia
#             # Setear los valores de la empresa
#             empresa=factura.proforma.cliente.empresa
#             context['empresa']={'nombre':empresa.nombre.upper(), 'correo':empresa.correo, 'telefono':empresa.telefono, 'direccion':empresa.direccion}
#             pdf = render_to_pdf('/home/backend/Documentos/administrador/backend_administrador/media_root/facturacion/pdfs/template.html', context)
#             filename = "factura_{}.pdf" %(factura.id)
#             factura.pdf.save(filename, File(BytesIO(pdf.content)))
#             return Response('Factura creada', status=status.HTTP_201_CREATED)
#         else:
#             raise Exception('Token del usuario invalido')
#     except Exception as e:
#         print('error',e)
#         context['error'] = e
#         return context

@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def hurt(request):
    # save = Proforma.objects.all()
    # try:
    #     ids = []
    #     for p in Proforma.objects.all():
    #         cobranza = DetalleNotasPago.objects.filter(proforma__exact = p)
    #         if not cobranza:
    #             exento = Decimal(0.0)
    #             imponible = Decimal(0.0)
    #             for d in DetalleProforma.objects.filter(proforma__exact = p):
    #                 producto = Producto.objects.get(id = d.producto.id)
    #                 if not producto.exonerado:
    #                     d.iva = d.total_producto*Decimal(16.0/100.0)
    #                     imponible += (d.total_producto + d.iva)
    #                 else:
    #                     exento += d.total_producto
    #                 # d.save()
    #             p.monto_exento = exento
    #             p.iva = imponible
    #             p.saldo_proforma = p.iva + p.monto_exento
    #             # p.save()
    #             ids.append(p.id)
    #     editados = []
    #     for id in ids:
    #         editado = TemporalProformasSerializer(Proforma.objects.get(id=id)).data
    #         editado['original'] = save.get(id=id).total
    #         editados.append(editado)
    #     return Response(editados, status=status.HTTP_200_OK)
    # except Exception as e:
    #     print(e)
    #     for p in save:
    #         p.save()
    #     return Response('Epa', status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(status=status.HTTP_501_NOT_IMPLEMENTED)