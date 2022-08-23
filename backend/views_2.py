# Importes de Rest framework
import enum
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
from django.db.models.functions import *
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
    permiso = 'NotaDevolucion'
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    # Datos
    modelo = NotaDevolucion
    queryset = modelo.objects.all()
    serializer_class = NotaDevolucionSerializer
    # Metodo crear
    def create(self,request):
        perfil = views.obt_per(self.request.user)
        if views.verificar_permiso(perfil,'NotaDevolucion','escribir'):
            datos = request.data
            try:
                datos['instancia'] = views.obtener_instancia(perfil,request.data['instancia'])
            except:
                datos['instancia'] = perfil.instancia.id
            datos['fecha_devolucion'] = timezone.now().date()
            configuracion = views.verificar_correlativo(datos,self.modelo)
            datos['correlativo'] = configuracion.valor
            serializer = self.get_serializer(data = datos)
            serializer.is_valid(raise_exception = True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            configuracion.valor+= 1
            configuracion.save()
            for d in datos['detalles']:
                detalle = DetalleNotaDevolucion.objects.create(
                    instancia = perfil.instancia,
                    nota_devolucion = serializer.data.id,
                    producto = d['producto'],
                    inventario = d['inventario'],
                    precio_seleccionado = d['precio_seleccionado'],
                    lote = d['lote'],
                    cantidada = d['cantidada'],
                    total_producto = d['total_producto'],
                )
                #NotaDevolucion
                views.modificar_inventario('devolver',detalle.inventario,detalle.cantidada)
            return Response(serializer.data,status = status.HTTP_201_CREATED,headers = headers)
        else:
            return Response(status = status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        return Response(status = status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil = views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','actualizar'):
        #     partial = True
        #     instance = self.get_object()
        #     try:
        #         if request.data['fecha_despacho']  ==  True and instance.fecha_despacho  ==  None:
        #             request.data['fecha_despacho'] = timezone.now()
        #     except Exception as e:
        #         print(e)
        #     if instance.instancia == perfil.instancia or perfil.tipo == 'S':
        #         serializer = self.get_serializer(instance,data = request.data,partial = partial)
        #         serializer.is_valid(raise_exception = True)
        #         self.perform_update(serializer)
        #         return Response(serializer.data,status = status.HTTP_200_OK)
        #     else:
        #         return Response(status = status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status = status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        return Response(status = status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil = views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','borrar'):
        #     instance = self.get_object()
        #     if instance.instancia == perfil.instancia or perfil.tipo == 'S':
        #         DetalleNotaDevolucion.objects.filter(nota_devolucion = instance.id).delete()
        #         instance.delete()
        #         return Response(status = status.HTTP_204_NO_CONTENT)
        #     else:
        #         return Response(status = status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status = status.HTTP_401_UNAUTHORIZED)
    # Metodos de leer
    def list(self,request):
        try:
            perfil = views.obt_per(self.request.user)
            if views.verificar_permiso(perfil,self.permiso,'leer'):
                instancia = perfil.instancia
                # Filtrar los objetos
                objetos = self.queryset if perfil.tipo == 'S' else self.queryset.filter(perfil__instancia = instancia)
                objetos = objetos.exclude(perfil__tipo__in = ['A','S']) if perfil.tipo == 'U' or perfil.tipo == 'V' else objetos
                # Paginacion
                paginado = views.paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data = self.serializer_class(paginado['objetos'],many = True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status = status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status = status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk = None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk = pk)).data) if views.verificar_permiso(views.obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status = status.HTTP_401_UNAUTHORIZED)

# Detalles de las notas de devolucion de la instancia
class DetalleNotaDevolucionVS(viewsets.ModelViewSet):
    # Permisos
    permiso = 'NotaDevolucion'
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    # Datos
    modelo = DetalleNotaDevolucion
    queryset = modelo.objects.all()
    serializer_class = DetalleNotaDevolucionSerializer
    # Metodo crear
    def create(self,request):
        return Response(status = status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil = views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','escribir'):
        #     datos = request.data
        #     try:
        #         datos['instancia'] = views.obtener_instancia(perfil,request.data['instancia'])
        #     except:
        #         datos['instancia'] = perfil.instancia.id
        #     serializer = self.get_serializer(data = datos)
        #     serializer.is_valid(raise_exception = True)
        #     self.perform_create(serializer)
        #     headers = self.get_success_headers(serializer.data)
        #     return Response(serializer.data,status = status.HTTP_201_CREATED,headers = headers)
        # else:
        #     return Response(status = status.HTTP_401_UNAUTHORIZED)
    def update(self,request,*args,**kwargs):
        return Response(status = status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil = views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','actualizar'):
        #     partial = True
        #     instance = self.get_object()
        #     if instance.instancia == perfil.instancia or perfil.tipo == 'S':
        #         serializer = self.get_serializer(instance,data = request.data,partial = partial)
        #         serializer.is_valid(raise_exception = True)
        #         self.perform_update(serializer)
        #         return Response(serializer.data,status = status.HTTP_200_OK)
        #     else:
        #         return Response(status = status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status = status.HTTP_401_UNAUTHORIZED)
    def destroy(self,request,*args,**kwargs):
        return Response(status = status.HTTP_405_METHOD_NOT_ALLOWED)
        # perfil = views.obt_per(self.request.user)
        # if views.verificar_permiso(perfil,'NotaDevolucion','borrar'):
        #     instance = self.get_object()
        #     inventario = Inventario.objects.get(id = instance.inventario.id)
        #     inventario.disponible = inventario.disponible+instance.cantidada
        #     if instance.instancia == perfil.instancia or perfil.tipo == 'S':
        #         instance.delete()
        #         inventario.save()
        #         return Response(status = status.HTTP_204_NO_CONTENT)
        #     else:
        #         return Response(status = status.HTTP_403_FORBIDDEN)
        # else:
        #     return Response(status = status.HTTP_401_UNAUTHORIZED)
    # Metodos de leer
    def list(self,request):
        try:
            perfil = views.obt_per(self.request.user)
            if views.verificar_permiso(perfil,self.permiso,'leer'):
                instancia = perfil.instancia
                # Filtrar los objetos
                objetos = self.queryset if perfil.tipo == 'S' else self.queryset.filter(perfil__instancia = instancia)
                objetos = objetos.exclude(perfil__tipo__in = ['A','S']) if perfil.tipo == 'U' or perfil.tipo == 'V' else objetos
                # Paginacion
                paginado = views.paginar(objetos,self.request.query_params.copy(),self.modelo)
                # Data e Info de la paginacion
                data = self.serializer_class(paginado['objetos'],many = True).data
                # Respuesta
                return Response({'objetos':data,'info':paginado['info']},status = status.HTTP_200_OK)
            else:
                raise
        except Exception as e:
            return Response('%s'%(e),status = status.HTTP_401_UNAUTHORIZED)
    def retrieve(self, request, pk = None):
        try:
            return Response(self.serializer_class(get_object_or_404(self.queryset, pk = pk)).data) if views.verificar_permiso(views.obt_per(request.user),self.permiso,'leer') else User.objects.none()
        except Exception as e:
            return Response('%s'%(e),status = status.HTTP_401_UNAUTHORIZED)













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
        return Response('Guardado',status = status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response('%s'%(e),status = status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def generar_lista_precio(request):
    params = request.query_params.copy()
    token = params.get('token').split(' ')[1]
    if Token.objects.get(key = token):
        perfil = Perfil.objects.get(usuario = 1)
        if views.verificar_permiso(perfil,'Productos','leer'):
            # Crear archivo temporal
            response = HttpResponse(content_type = 'application/ms-excel')
            response['Content-Disposition'] = 'attachment;filename = "lista_precios.xls"'
            # Iniciar Excel
            excel_wb = Workbook(encoding = 'utf-8')
            excel_ws = excel_wb.add_sheet('Hoja1') # ws es Work Sheet
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
            i = 4 # Saltador de fila
            # Escribir nombres de las columnas
            ahora = datetime.datetime.now()
            estilo_dia = easyxf('font: bold 1, height 300; align: wrap on, horiz center')
            celdas_nombre_marca = []
            excel_ws.write(i,0,'LISTA DE PRECIOS AL: %s/%s/%s'%(ahora.day,ahora.month,ahora.year),estilo_dia)
            celdas_nombre_marca.append(i)
            i = i+2 # Saltador de fila    
            excel_ws.write(i,0,'DESCRIPCIÓN',estilo_cabezera)
            excel_ws.write(i,1,'MARCA',estilo_cabezera)
            excel_ws.write(i,2,'PRECIO',estilo_cabezera)
            excel_ws.write(i,3,'IVA',estilo_cabezera)
            excel_ws.set_panes_frozen(True)
            excel_ws.set_horz_split_pos(7)
            # Ciclo por cada marca
            marcas_elegidas = params.get('marcas').split(',')
            for id_marca in marcas_elegidas if marcas_elegidas[0] != '0' else Marca.objects.all().values_list('id'):
                marca = Marca.objects.get(id = id_marca if type(id_marca) != type(()) else id_marca[0])
                i = i+2 # Saltar fila
                # Ciclo por cada producto
                excel_ws.write(i,0,marca.nombre,estilo_nombre_marca)
                celdas_nombre_marca.append(i)
                i = i+1 # Saltar fila
                for p in Producto.objects.filter(marca = marca).order_by('nombre').values():
                    i = i+1 # Saltar fila
                    # Escribir productos
                    # excel_ws.write(i,0,m['nombre']) # Nombre marca
                    # excel_ws.write(i,1,p['sku']) # Codigo producto
                    excel_ws.write(i,0,p['nombre'],lefted) # Nombre producto
                    excel_ws.write(i,1,marca.nombre,centered) # Nombre producto
                    precio = None
                    # Precios del producto
                    if params.get('precio')  ==  'precio_1':
                        precio = round(p['precio_1'],2)
                    elif params.get('precio')  ==  'precio_2':
                        precio = round(p['precio_2'],2)
                    elif params.get('precio')  ==  'precio_3':
                        precio = round(p['precio_3'],2)
                    elif params.get('precio')  ==  'precio_4':
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
            return Response(status = status.HTTP_401_UNAUTHORIZED)
    else:
        return Response(status = status.HTTP_403_FORBIDDEN)
    return Response('',status = status.HTTP_501_NOT_IMPLEMENTED)

data_temporal = {'vendedor':0}

def formato_coma(valor):
    str(valor).replace('.',',')
    return valor

@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def analisis_vencimiento(request):
    params = request.query_params.copy()
    usuario = Token.objects.get(key = params.get('token').split(' ')[1]).user
    # if usuario:
    data = int(params.get('vendedor'))
    if not data:
        data = data_temporal['vendedor']
    perfil = Perfil.objects.get(usuario = 1)
    if views.verificar_permiso(perfil,'Productos','leer'):
        response = HttpResponse(content_type = 'application/ms-excel')
        response['Content-Disposition'] = 'attachment;filename = "analisis_vencimiento.xls"'
        # Iniciar Excel
        excel_wb = Workbook(encoding = 'utf-8')
        excel_ws = excel_wb.add_sheet('Hoja1') # ws es Work Sheet
        # Añadiendo estilo
        excel_ws.col(0).width = 2700 # Tamaño columna numero NotaDevolucion
        excel_ws.col(1).width = 5000 # Tamaño columna emision NotaDevolucion
        excel_ws.col(2).width = 5000 # Tamaño columna despacho NotaDevolucion
        excel_ws.col(3).width = 3900 # Tamaño columna monto total NotaDevolucion
        excel_ws.col(4).width = 3900 # Tamaño columna saldo NotaDevolucion
        excel_ws.col(5).width = 1500 # Tamaño columna dias Despacho/Hoy
        bold = easyxf('font: bold 1')
        center = easyxf('align: wrap on, horiz center')
        number = easyxf('')
        number.num_format_str = '0.00'
        vendedores = Vendedor.objects.filter(instancia = Perfil.objects.get(usuario = usuario).instancia)
        vendedores = vendedores.filter(id__exact = data) if data != 0 else vendedores
        ahora = timezone.now()
        i = 0
        background_a = easyxf('pattern: pattern solid')
        background_b = easyxf('pattern: pattern solid; font: bold 1')
        background_b.font.colour_index = Style.colour_map['white']
        background_c = easyxf('pattern: pattern solid')
        background_d = easyxf('pattern: pattern solid')
        background_e = easyxf('pattern: pattern solid; font: bold 1')
        background_f = easyxf('pattern: pattern solid; font: bold 1; align: wrap on, horiz right')
        background_g = easyxf('pattern: pattern solid; font: bold 1; align: wrap on, horiz right')
        background_a.pattern.pattern_fore_colour = 0x37
        background_b.pattern.pattern_fore_colour = 0x3F
        background_c.pattern.pattern_fore_colour = 0x16
        background_d.pattern.pattern_fore_colour = 0x16
        background_e.pattern.pattern_fore_colour = 0x16
        background_f.pattern.pattern_fore_colour = 0x16
        background_g.pattern.pattern_fore_colour = 0x37
        bold_number = easyxf('font: bold 1')
        bold_number.num_format_str = '0.00'
        excel_ws.write(i,0,'ANALISIS DE VENCIMIENTO CTAS x COBRAR al: %s'%(ahora.date()),bold)
        filas_divisoras = []
        filas_sumatorias = []
        sumatorias = []
        total_analisis = 0
        for vendedor in vendedores:
            proformas_vendedor = Proforma.objects.filter(vendedor = vendedor).exclude(saldo_proforma = Decimal(0.0))
            total_saldo = Decimal(0.0)
            if proformas_vendedor:
                i += 2
                excel_ws.write(i,0,'VENDEDOR: %s, CODIGO: %s'%(vendedor.nombre,vendedor.codigo),background_b)
                for c in [1,2,3,4,5]:
                    excel_ws.write(i,c,'',background_b)
                # for c in [0,1,2,3,4,5]:
                #     excel_ws.write(i,c,'',background_c)
                fondo_temp = 0
                clientes = Cliente.objects.filter(vendedor = vendedor).order_by('codigo')
                pendiente = 0
                for cliente in clientes:
                    total = 0
                    proformas_cliente = proformas_vendedor.filter(cliente = cliente)
                    if proformas_cliente:
                        fondo_temp += 1
                        fondo_blanco = fondo_temp % 2
                        i += 1
                        for c in [0,1,2,3,4,5]:
                            excel_ws.write(i,c,'', easyxf('') if fondo_blanco else background_c)
                        i += 1
                        excel_ws.write(i,0,'CLIENTE:',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,1,'%s %s'%(cliente.codigo,cliente.nombre),background_e if not fondo_blanco else bold)
                        excel_ws.write(i,2,'',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,3,'RIF: %s'%(cliente.identificador),background_e if not fondo_blanco else bold)
                        excel_ws.write(i,4,'Telf: %s'%(cliente.telefono),background_e if not fondo_blanco else bold)
                        excel_ws.write(i,5,'',background_e if not fondo_blanco else bold)
                        i += 1
                        excel_ws.write(i,0,'Proforma',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,1,'Fecha Emis',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,2,'Fecha Desp',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,3,'Monto Emis',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,4,'Saldo',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,5,'Dias',background_e if not fondo_blanco else bold)
                        i += 1
                        for proforma in proformas_cliente:
                            correlativo = Correlativo.objects.get(empresa = proforma.empresa,tipo = "E")
                            excel_ws.write(i,0,'%s%s'%(correlativo.prefijo+'-' if correlativo.prefijo else '',proforma.correlativo),background_c if not fondo_blanco else easyxf(''))
                            excel_ws.write(i,1,'%s'%(proforma.fecha_proforma.date()),background_c if not fondo_blanco else easyxf(''))
                            if proforma.fecha_despacho:
                                excel_ws.write(i,2,'%s'%(proforma.fecha_despacho.date()),background_c if not fondo_blanco else easyxf(''))
                                excel_ws.write(i,5,'%s'%((ahora.date() - proforma.fecha_despacho.date()).days),background_c if not fondo_blanco else easyxf(''))
                            else:
                                excel_ws.write(i,2,'Sin despachar',background_c if not fondo_blanco else easyxf(''))
                                excel_ws.write(i,5,'-',background_c if not fondo_blanco else easyxf(''))
                            total_proforma = round(proforma.iva + proforma.exento,2)
                            saldo_proforma = round(proforma.saldo_proforma,2)
                            # if len(total_proforma.split('.')[1])  ==  1: total_proforma = total_proforma + '0'
                            # if len(saldo_proforma.split('.')[1])  ==  1: saldo_proforma = saldo_proforma + '0'
                            excel_ws.write(i,3,total_proforma,background_d if not fondo_blanco else number)
                            excel_ws.write(i,4,saldo_proforma,background_d if not fondo_blanco else number)
                            total += round(total_proforma,2)
                            pendiente += round(saldo_proforma,2)
                            i += 1
                        excel_ws.write(i,0,'',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,1,'TOTAL CLIENTE %s:'%(cliente.codigo),background_e if not fondo_blanco else bold)
                        excel_ws.write(i,2,'',background_e if not fondo_blanco else bold)
                        excel_ws.write(i,3,round(total,2),background_f if not fondo_blanco else bold_number)
                        excel_ws.write(i,4,round(pendiente,2),background_f if not fondo_blanco else bold_number)
                        excel_ws.write(i,5,'',background_e if not fondo_blanco else bold)
                        total_saldo += pendiente
                        i += 1
                        for c in [0,1,2,3,4,5]:
                            excel_ws.write(i,c,'',background_c if not fondo_blanco else easyxf(''))
                        i += 1
                        filas_divisoras.append(i)
                filas_sumatorias.append(i)
                sumatorias.append(total_saldo)
                total_analisis += total_saldo
        i += 1
        for fd in filas_divisoras:
            no = False
            for ie, fs in enumerate(filas_sumatorias):
                if fd > 8 and fd  ==  fs:
                    no = True
                    excel_ws.write(fd,0,'',background_a)
                    excel_ws.write(fd,1,'',background_a)
                    excel_ws.write(fd,2,'',background_a)
                    excel_ws.write(fd,3,'%s'%('TOTAL:'),background_g)
                    excel_ws.write(fd,4,formato_coma(sumatorias[ie]),background_g)
                    excel_ws.write(fd,5,'',background_a)
            if not no and fd > 0:
                for c in [0,1,2,3,4,5]:
                    excel_ws.write(fd,c,'', background_a)
        i += 1
        excel_ws.write(i,3,'%s'%('TOTAL V:'),bold_number)
        excel_ws.write(i,4,round(total_analisis,2),bold_number)
        # Guardado temporal del excel
        excel_wb.save(response)
        # Retornar y generar
        return response
    return Response('',status = status.HTTP_501_NOT_IMPLEMENTED)
    # else:
    #     return Response(status = status.HTTP_403_FORBIDDEN)


def crear_factura(context,kwargs):
    context['error'] = None
    try:
        if Token.objects.get(key = kwargs['token']):
            conversion = None
            factura = Factura.objects.get(id = kwargs['id_factura'])
            try:
                conversion = factura.tasa_c
            except:
                conversion = TasaConversion.objects.latest('fecha_tasa')
            subtotal = Decimal(float(factura.subtotal))
            total_costo = round(Decimal(float(factura.total)) * conversion.valor, 2)
            value = {'data':[]}
            total_exento = Decimal(0.0)
            total_imponible = Decimal(0.0)
            total_calculado = Decimal(0.0)
            # Ciclo para generar Json y data para el template
            for dato in DetalleFactura.objects.filter(factura = factura).values('id', 'producto', 'precio').annotate(total = Sum('total_producto'), cantidad = Sum('cantidada')):
                productox = Producto.objects.get(id = dato['producto'])
                valuex = {'datax':[]}
                total_cantidad = 0
                precio_unidad = 0.0
                costo_total = 0.0
                mostrar = True
                detallado = DetalleFactura.objects.filter(factura = factura, producto = productox).order_by('producto__id')
                if productox.lote == True and len(detallado) > 1:
                    for detalle in detallado:
                        valuex['datax'].append({'lote':detalle.lote if detalle.lote else 'Sin lote', 'cantidad':detalle.cantidada, 'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''})
                        total_cantidad += int(detalle.cantidada)
                        precio_unidad = round(Decimal(float(detalle.precio)) * conversion.valor,2)
                elif productox.lote == True and len(detallado) == 1:
                    valuex['datax'] = ''
                    mostrar = False
                    for detalle in detallado:
                        valuex['datax'] = {'lote':detalle.lote, 'vencimiento':detalle.inventario.fecha_vencimiento.date() if detalle.inventario else ''}
                        total_cantidad += int(detalle.cantidada)
                        precio_unidad = round(Decimal(float(detalle.precio)) * conversion.valor,2)
                else:
                    mostrar = False
                    for detalle in detallado:
                        total_cantidad += int(detalle.cantidada)
                        precio_unidad = round(Decimal(float(detalle.precio)) * conversion.valor,2)
                    valuex['datax'] = None
                costo_total = round(precio_unidad * Decimal(float(total_cantidad)),2)
                if productox.exonerado  ==  False:
                    total_imponible += costo_total
                else:
                    total_exento += costo_total
                total_calculado += costo_total
                extra_cero_precio = True if len(str(round(precio_unidad, 2)).split('.')[1]) < 2 else False
                extra_cero_total = True if len(str(round(costo_total, 2)).split('.')[1]) < 2 else False
                value['data'].append({'producto_nombre':productox.nombre, 'extra_cero_precio':extra_cero_precio, 'extra_cero_total':extra_cero_total, 'exento':productox.exonerado, 'producto_sku':productox.sku, 'detalle':valuex['datax'], 'mostrar':mostrar, 'cantidad':total_cantidad, 'precio':round(precio_unidad, 2), 'total_producto':round(costo_total, 2)})
            # subtotal_conversion = round(subtotal * conversion.valor,2)
            # Sumatoria de los no exentos (Imponible)
            total_imponible = round(total_imponible,2)
            # Sumatoria de los exentos (Exonerados)
            total_exento = round(total_exento,2)
            subtotal_conversion = round(total_imponible + total_exento,2)
            # 16% (IVA)
            iva = round(total_imponible*Decimal(16/100), 2)
            total_real = subtotal_conversion
            if total_imponible:
                total_real = subtotal_conversion + iva
            # Setear los valores al template
            context['productos'] = value['data']
            context['subtotal'] = subtotal_conversion
            context['extra_cero_subtotal'] = True if len(str(subtotal_conversion).split('.')[1]) < 2 else False
            context['imponible'] = total_imponible
            context['extra_cero_imponible'] = True if len(str(total_imponible).split('.')[1]) < 2 else False
            context['exento'] = total_exento
            context['extra_cero_exento'] = True if len(str(total_exento).split('.')[1]) < 2 else False
            context['impuesto'] = iva
            context['extra_cero_impuesto'] = True if len(str(iva).split('.')[1]) < 2 else False
            context['total'] = total_real
            context['extra_cero_total_real'] = True if len(str(total_real).split('.')[1]) < 2 else False
            context['factura'] = factura
            context['correlativo_proforma'] = factura.proforma.correlativo
            # Setear los valores de la empresa
            empresa = factura.proforma.cliente.empresa
            context['empresa'] = {'nombre':empresa.nombre.upper(), 'correo':empresa.correo, 'telefono':empresa.telefono, 'direccion':empresa.direccion}
            return context
        else:
            raise Exception('Token del usuario invalido')
    except Exception as e:
        print('error',e)
        context['error'] = e
        return context

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
    #             p.exento = exento
    #             p.iva = imponible
    #             p.saldo_proforma = p.iva + p.exento
    #             # p.save()
    #             ids.append(p.id)
    #     editados = []
    #     for id in ids:
    #         editado = TemporalProformasSerializer(Proforma.objects.get(id = id)).data
    #         editado['original'] = save.get(id = id).total
    #         editados.append(editado)
    #     return Response(editados, status = status.HTTP_200_OK)
    # except Exception as e:
    #     print(e)
    #     for p in save:
    #         p.save()
    #     return Response('Epa', status = status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(status = status.HTTP_501_NOT_IMPLEMENTED)

def generate_password(data):
    hora = datetime.datetime.now()
    mail = data.correo
    name = data.nombre
    return 'hola'

@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def migrar_vendedores(request):
    for v in Vendedor.objects.all():
        if not User.objects.filter(username = v.nombre):
            usuario = User.objects.create_user(username = v, email = v, password = print(generate_password(v)))
    return Response(status = status.HTTP_501_NOT_IMPLEMENTED)

meses = [
    "ninguno",
    "enero",
    "febero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

def obtener_mes(mes):
    return meses[mes]

def formatear_numero(enteros, decimales, valor):
    try:
        valor_dividido = str(valor).split('.')
    except:
        valor_dividido = str(valor)
    restante = 0
    n_valor = ''
    if enteros and valor_dividido[0]:
        ne_valor = str(valor_dividido[0])[::-1]
        restante = enteros - len(ne_valor)
        if restante > 0:
            for r in range(restante):
                ne_valor = ne_valor + '0'
        elif restante < 0:
            for r in range(restante*-1):
                ne_valor = ne_valor[:-1]
        ne_valor = ne_valor[::-1]
    else:
        ne_valor = 0
    n_valor = ne_valor
    if decimales and len(valor_dividido) > 1:
        nd_valor = str(valor_dividido[1])
        restante = enteros - len(nd_valor)
        if restante > 0:
            for r in range(restante):
                nd_valor = nd_valor + '0'
        elif restante < 0:
            for r in range(restante*-1):
                nd_valor = nd_valor[:-1]
        n_valor = n_valor + ',' + nd_valor
    return n_valor

def convertir(valor, tasa):
    return valor * tasa

# Funcion tipo vista para generar Excel con el libro de venta en base a una fecha inicio, fecha fin
@api_view(["POST", "GET"])
@csrf_exempt
def generar_libro_venta(request):
    params = request.query_params.copy()
    token = params.get('token').split(' ')[1]
    user = Token.objects.get(key = token).user
    if user:
        data = {'fecha_inicio': params.get('fecha_inicio'), 'fecha_fin': params.get('fecha_fin')}
        empresa = Empresa.objects.get(id = params.get('empresa'))
        perfil = Perfil.objects.get(usuario = user)
        try:
            if views.verificar_permiso(perfil, 'LibroVenta', 'leer'):
                """ Data inicial """
                # Obtner el rango de fechas para el filtro
                ini = data['fecha_inicio'].split('/')
                fecha_inicio = ini[0] + '-' + ini[1] + '-' + ini[2] # Formateando Date inicial para timezone
                date_inicio = datetime.date(year=int(ini[0]),month=int(ini[1]),day=int(ini[2]))
                fin = data['fecha_fin'].split('/')
                date_fin = datetime.date(year=int(fin[0]),month=int(fin[1]),day=int(fin[2]))
                fecha_fin = fin[0] + '-' + fin[1] + '-' + fin[2] # Formateando Date final para timezone
                rango = [fecha_inicio, fecha_fin] # Rango
                tardio = timezone.now()-timezone.timedelta(weeks = 4) # Tiempo maximo de 30 dias
                # Filtrar Facturas
                facturas = Factura.objects.filter(proforma__empresa = empresa,fecha_factura__date__range = rango).annotate(control_int=Cast('control', IntegerField())).order_by('control_int')
                # Excel
                i = 0
                response = HttpResponse(content_type = 'application/ms-excel')
                response['Content-Disposition'] = 'attachment;filename = "libro_venta_%s&%s.xls"' % (fecha_inicio, fecha_fin)
                excel_wb = Workbook(encoding = 'utf-8')
                excel_ws = excel_wb.add_sheet('Libro1') # ws es Work Sheet
                # Añadiendo estilo
                excel_ws.col(0).width = 1000 # Tamaño columna fecha documento
                excel_ws.col(1).width = 3500 # Tamaño columna fecha documento
                excel_ws.col(2).width = 3500 # Tamaño columna rif cliente
                excel_ws.col(3).width = 17000 # Tamaño columna nombre cliente
                excel_ws.col(4).width = 3000 # Tamaño columna tipo documento
                excel_ws.col(5).width = 3000 # Tamaño columna numero de documento
                excel_ws.col(6).width = 3000 # Tamaño columna numero de control
                excel_ws.col(7).width = 3900 # Tamaño columna total documento
                excel_ws.col(8).width = 3900 # Tamaño columna total exento
                excel_ws.col(9).width = 3900 # Tamaño columna total imponible
                excel_ws.col(10).width = 3900 # Tamaño columna total impuesto
                estilo = easyxf('font: bold 1')
                lefted = easyxf('align: wrap on, horiz left')
                centered = easyxf('align: wrap on, horiz center')
                number = easyxf('')
                number.num_format_str = '0.00'
                bold_number = easyxf('font: bold 1')
                number.num_format_str = '0.00'
                # Encabezado
                excel_ws.write(i, 0, '%s'%(empresa.nombre), estilo)
                i = i + 1
                excel_ws.write(i, 0, 'R.I.F.: %s'%(empresa.rif), estilo)
                i = i + 1
                excel_ws.write(i, 0, 'Direccion: %s'%(empresa.direccion), estilo)
                i = i + 2
                excel_ws.write(i, 2, 'VENTAS CORRESPONDIENTES AL MES %s. Desde: %s, hasta: %s'%(obtener_mes(date_fin.month).upper(),date_inicio,date_fin), estilo)
                i = i + 1
                # Primera fila del excel
                i = i + 1
                excel_ws.write(i, 0, 'Nro.', estilo)
                excel_ws.write(i, 1, 'Fecha', estilo)
                excel_ws.write(i, 2, 'Nº Rif', estilo)
                excel_ws.write(i, 3, 'Nombre o razón social', estilo)
                excel_ws.write(i, 4, 'Tipo Doc.', estilo)
                excel_ws.write(i, 5, 'Nº Doc.', estilo)
                excel_ws.write(i, 6, 'Nº Control', estilo)
                excel_ws.write(i, 7, 'Total Doc.', estilo)
                excel_ws.write(i, 8, 'Total Exento', estilo)
                excel_ws.write(i, 9, 'Total Imponible', estilo)
                excel_ws.write(i, 10, 'Total Impuesto', estilo)
                i = i + 1
                total_libro = 0
                total_libro_iva = 0
                total_exento = 0
                total_imponible = 0
                counter = 0
                # Creador de filas
                for f in facturas:
                    total = Decimal(0.0)
                    if f.proforma:
                        counter += 1
                        excel_ws.write(i, 0, counter)
                        excel_ws.write(i, 1, '%s' % (f.fecha_factura.date()),centered)
                        excel_ws.write(i, 2, '%s' % (f.identificador_fiscal),)
                        excel_ws.write(i, 3, '%s' % (f.nombre_cliente),)
                        excel_ws.write(i, 4, 'FACTURA',)
                        excel_ws.write(i, 5, '%s' % (f.correlativo),centered)
                        excel_ws.write(i, 6, '00-%s' % (formatear_numero(6, 0, f.control)),centered)
                        excel_ws.write(i, 7, convertir(f.proforma.exento + f.proforma.iva, f.tasa_c.valor),number) # Arreglos temporales
                        total_libro += convertir(f.proforma.exento + f.proforma.iva, f.tasa_c.valor)
                        excel_ws.write(i, 8, convertir(f.proforma.exento, f.tasa_c.valor),number) # Arreglos temporales
                        total_exento += convertir(f.proforma.exento, f.tasa_c.valor)
                        excel_ws.write(i, 9, round(convertir(Decimal(f.total) - f.proforma.exento, f.tasa_c.valor),2),number) # Arreglos temporales
                        total_imponible += round(convertir(Decimal(f.total) - f.proforma.exento, f.tasa_c.valor),2)
                        if not f.iva or (f.iva == 16 and (f.exento - f.subtotal) == 100):
                            print('holo')
                            for df in DetalleFactura.objects.filter(factura = f):
                                total += convertir(Decimal(df.iva), f.tasa_c.valor)
                            excel_ws.write(i, 10, convertir(total, f.tasa_c.valor),number) # Arreglos temporales
                        else:
                            total = convertir(Decimal(f.iva), f.tasa_c.valor)
                            excel_ws.write(i, 10, convertir(total, f.tasa_c.valor),number) # Arreglos temporales
                        total_libro_iva += total
                        i = i + 1
                excel_ws.write(i, 7, total_libro,bold_number)
                excel_ws.write(i, 8, total_exento,bold_number)
                excel_ws.write(i, 9, total_imponible,bold_number)
                excel_ws.write(i, 10,total_libro_iva,bold_number)
                excel_wb.save(response)
                number.num_format_str = '0.00'
                return response
            else:
                return Response(status = status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(e)
            return Response('%s' % (e), status = status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status = status.HTTP_403_FORBIDDEN)


# Funcion tipo vista para generar Excel con el libro de venta en base a una fecha inicio, fecha fin
@api_view(["POST", "GET"])
@csrf_exempt
def generar_historico_proformas(request):
    # Iniciar vista
    params = request.query_params.copy() # Obtener parametros
    token = params.get('token').split(' ')[1] # Obtener token del parametro
    user = Token.objects.get(key = token).user # Obtener usuriao con el token
    if user: # Verifircar que exista el usuario
        try:
            if views.verificar_permiso(Perfil.objects.get(usuario = user), 'LibroVenta', 'leer'): # Verificar permiso del usuario para ver reportes
                data = {'fecha_inicio': params.get('fecha_inicio'), 'fecha_fin': params.get('fecha_fin')} # Obtener rango del reporte
                """ Data inicial """
                # Obtner el rango de fechas para el filtro
                ini = data['fecha_inicio'].split('/');  fecha_inicio = ini[0] + '-' + ini[1] + '-' + ini[2] # Formateando Date inicial para timezone
                fin = data['fecha_fin'].split('/');     fecha_fin = fin[0] + '-' + fin[1] + '-' + fin[2] # Formateando Date final para timezone
                rango = [fecha_inicio, fecha_fin] # Rango del reporte
                tardio = timezone.now()-timezone.timedelta(weeks = 4) # Tiempo maximo de 30 dias
                # Filtrar proformas y devoluciones
                proformas = Proforma.objects.filter(fecha_proforma__date__range = rango)
                devoluciones = NotaDevolucion.objects.filter(fecha_devolucion__date__range = rango)
                # Excel
                i = 0 # Iniciar saltador de linea
                response = HttpResponse(content_type = 'application/ms-excel')
                response['Content-Disposition'] = 'attachment;filename = "historico_proforma_%s&%s.xls"' % (fecha_inicio, fecha_fin)
                excel_wb = Workbook(encoding = 'utf-8')
                excel_ws = excel_wb.add_sheet('Libro1') # ws es Work Sheet
                # Añadiendo estilo
                excel_ws.col(0).width = 3500 # Tamaño columna fecha del documento
                excel_ws.col(1).width = 3500 # Tamaño columna rif del cliente
                excel_ws.col(2).width = 16000 # Tamaño columna nombre del cliente
                excel_ws.col(3).width = 3000 # Tamaño columna tipo de documento
                excel_ws.col(4).width = 2600 # Tamaño columna correlativo del documento
                # excel_ws.col(5).width = 2600 # Tamaño columna correlativo del control
                excel_ws.col(6).width = 2600 # Tamaño columna total del documento
                excel_ws.col(7).width = 2600 # Tamaño columna total del imponible
                excel_ws.col(8).width = 2600 # Tamaño columna total del iva neto
                estilo = easyxf('font: bold 1')
                centered = easyxf('align: wrap on, horiz center')
                number = easyxf('')
                number.num_format_str = '0.00'
                """ CREACION DEL REPORTE"""
                # Encabezado del reporte
                excel_ws.write(i, 0, 'Fecha', estilo)
                excel_ws.write(i, 1, 'Nº Rif', estilo)
                excel_ws.write(i, 2, 'Nomempresabre o razón social', estilo)
                excel_ws.write(i, 3, 'Tipo Doc.', estilo)
                excel_ws.write(i, 4, 'Nº Doc.', estilo)
                excel_ws.write(i, 5, 'Nº Control', estilo)
                excel_ws.write(i, 6, 'Total Doc.', estilo)
                excel_ws.write(i, 7, 'Total Exento', estilo)
                excel_ws.write(i, 8, 'Total Imponible', estilo)
                excel_ws.write(i, 9, 'Total Impuesto', estilo)
                i = i + 1 # Saltador de linea
                # Iniciar valores finales del reporte
                total_libro = 0
                total_libro_iva = 0
                total_exento = 0
                total_imponible = 0
                # Ciclo creador de filas
                for p in proformas:
                    total = 0
                    # Obtener devoluciones de la proforma
                    devoluciones_proforma = devoluciones.filter(proforma = p)
                    if devoluciones_proforma:
                        for d in devoluciones_proforma:
                            excel_ws.write(i, 0, '%s' % (d.fecha_proforma.date()),centered)
                            # ...
                    else:
                        # Valores basicos
                        excel_ws.write(i, 0, '%s' % (p.fecha_proforma.date()), centered)
                        excel_ws.write(i, 1, '%s' % (p.identificador_fiscal))
                        excel_ws.write(i, 2, '%s' % (p.nombre_cliente))
                        excel_ws.write(i, 3, 'PROFORMA',)
                        excel_ws.write(i, 4, '%s' % (p.correlativo), centered)
                        # Valores numericos
                        excel_ws.write(i, 6, (p.exento + p.iva), number);                         total_libro += p.exento + p.iva # Sumar al total del reporte
                        excel_ws.write(i, 7, p.exento, number);                                   total_exento += p.exento # Sumar al total exento del reporte
                        excel_ws.write(i, 8, round(float(p.total)-float(p.exento),2), number);    total_imponible += round(float(p.total)-float(p.exento),2) # Sumar al total impnible del reporte
                        # Ciclo para obtener el iva total neto
                        for dp in DetalleProforma.objects.filter(proforma = p): total += Decimal(dp.iva)
                        # Total iva del reporte
                        excel_ws.write(i, 9, total, number); total_libro_iva += total
                    # ENDIF
                    i = i + 1 # Saltar fila
                # Valores totales del reporte
                excel_ws.write(i, 6, total_libro, number)
                excel_ws.write(i, 7, total_exento, number)
                excel_ws.write(i, 8, total_imponible, number)
                excel_ws.write(i, 9, total_libro_iva, number)
                # Guardar y retornar
                excel_wb.save(response); return response
            else:
                return Response(status = status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(e); return Response('%s' % (e), status = status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status = status.HTTP_403_FORBIDDEN)


@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def arreglar_facturas(request):
    arregladas = []
    for factura in Factura.objects.all():
        error = True
        fecha = factura.fecha_factura.date()
        tasa_1 = TasaConversion.objects.filter(fecha_tasa__date = fecha).first()
        tasa_2 = None
        tasa_3 = None
        tasa_4 = None
        tasa = None

        if tasa_1 and not tasa:
            tasa = tasa_1
            arregladas.append({'factura': factura.nombre_empresa + ' - ' + factura.correlativo,'tasa': 'Del mismo dia'})
        else:
            fecha = fecha - datetime.timedelta(days=1)
            tasa_2 = TasaConversion.objects.filter(fecha_tasa__date = fecha).first()

        if tasa_2 and not tasa:
            tasa = tasa_2
            arregladas.append({'factura': factura.nombre_empresa + ' - ' + factura.correlativo,'tasa': '1 dia antes'})
        else:
            fecha = fecha - datetime.timedelta(days=1)
            tasa_3 = TasaConversion.objects.filter(fecha_tasa__date = fecha).first()

        if tasa_3 and not tasa:
            tasa = tasa_3
            arregladas.append({'factura': factura.nombre_empresa + ' - ' + factura.correlativo,'tasa': '2 dias antes'})
        else:
            tasa_4 = TasaConversion.objects.latest('id')

        if tasa_4 and not tasa:
            tasa = tasa_4
            arregladas.append({'factura': factura.nombre_empresa + ' - ' + factura.correlativo,'tasa': 'Ultima creada'})
        
        factura.tasa_c = tasa
        factura.save()
    return Response(arregladas,status=status.HTTP_200_OK)