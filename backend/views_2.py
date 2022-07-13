# Importes de Rest framework
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
# from .vistas import *
# Recuperar contraseña
from knox.views import LoginView as KnoxLoginView
from django.conf import settings
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.template.loader import render_to_string
# Utiles
from django_renderpdf.views import PDFView
from email import header
from urllib import response
from numpy import indices, safe_eval
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













@api_view(["GET"])
@csrf_exempt
@authentication_classes([BasicAuthentication])
@permission_classes([AllowAny])
def lista_precio(request):
    data = request.data
    print(data)
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
            proformas_vendedor = Proforma.objects.filter(vendedor=vendedor).exclude(saldo_proforma=0.0)
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
