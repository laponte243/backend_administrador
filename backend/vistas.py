from os import stat_result
import re
from rest_framework import permissions
from rest_framework import viewsets,status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authentication import SessionAuthentication,BasicAuthentication,TokenAuthentication
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.permissions import IsAdminUser,IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework.utils import json
from django_filters.rest_framework import DjangoFilterBackend
# Importes de Django
from django.apps import apps
from django.db.models import Count,Q,Sum
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers as sr
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse,HttpResponse,request
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
# Raiz
from .serializers import *
from .models import *
from .menu import *
from .views import *
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
from numpy import indices
import pandas as pd
import csv
import xlwt
import requests
import datetime
import random
import string
""" Funciones y funciones tipo vistas """
# Reseteo de contraseña
@receiver(reset_password_token_created)
def password_reset_token_created(sender,instance,reset_password_token,*args,**kwargs):
    RESET_PASSWORD_ROUTE=getattr(settings,"RESET_PASSWORD_ROUTE",None)
    # email_plaintext_message="{}?token={}".format(reverse('password_reset:reset-password-request'),reset_password_token.key)
    context=({"url": RESET_PASSWORD_ROUTE+'#/passwordset?token='+reset_password_token.key})
    resetPasswordTemplate='user_reset_password.html'
    reset_password_message=render_to_string(resetPasswordTemplate,context)
    # Send email
    subject,from_email,to="Password Reset for {title}".format(title="DataVisualizer"),'noreply@somehost.local',reset_password_token.user.email
    text_content=''
    html_content=reset_password_message
    msg=EmailMessage(subject,html_content,from_email,[to])
    msg.content_subtype="html"  # Main content is now text/html
    msg.send()
# Funcion tipo vista para obtener objetos del inventario
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def inventario(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Inventario','leer'):
        if perfil:
            inventarios=Inventario.objects.filter(instancia=perfil.instancia)
            for o in inventarios:
                if o.disponible==0 and o.bloqueado==0:
                    inventarios=inventarios.exclude(id=o.id)
            inventarios=inventarios.values('almacen','almacen__nombre','producto','producto__nombre').annotate(sum_disponible=Sum('disponible'),sum_bloqueado=Sum('bloqueado'))
            return Response(inventarios,status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para crear un nuevo usuario
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def crear_nuevo_usuario(request):
    datos=request.data
    user=None
    perfil_nuevo=None
    try:
        perfil_creador=Perfil.objects.get(usuario=request.user)
        # En caso de encontrar un usuario con el mismo email
        user=User.objects.filter(email=datos['email'])
        if user:
            return Response("Ya hay un usuario con el mismo correo",status=status.HTTP_400_BAD_REQUEST)
        # En caso de crear un nuevo Admin
        elif perfil_creador.tipo=='S' and datos['tipo']=='A':
            return crear_admin(datos,perfil_creador)
        # En caso de que se quiera crear un usuario normal
        elif perfil_creador.tipo=='A' or perfil_creador.tipo=='S' or verificar_permiso(perfil_creador,'Usuarios_y_permisos','escribir'):
            # Obtencion rapida de la instancia
            datos['instancia']=obtener_instancia(perfil_creador,datos['instancia'])
            # Crear usuario con 'create_user'
            user=User.objects.create_user(username=datos['username'],email=datos['email'],password=datos['clave'])
            # Crear perfil del usuario
            perfil_nuevo=Perfil.objects.create(usuario=user,instancia_id=datos['instancia'],tipo=datos['tipo'])
            # Crear permisos
            permisos=guardar_permisos(datos['permisos'],perfil_nuevo.id,perfil_creador)
            # En caso de un error al crear los permisos saltar error
            if permisos:
                raise Exception('%s'%(permisos['error']))
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        # Borrar datos en caso de error
        try:
            user.delete()
        except:
            pass
        try:
            perfil_nuevo.delete()
        except:
            pass
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo vista para obtener el menu de la pagina segun el perfil, los permisos y la intancia del usuario
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def obtener_menu(request):
    menus={ 'router': 'root','children': []}
    usuario=request.user
    def VerificarHijos(objetoPadre):
        if (MenuInstancia.objects.filter(parent=objetoPadre.id).count() > 0 or Menu.objects.filter(parent=objetoPadre.id).count() > 0):
            return True
        else:
            return False
    if usuario.perfil.tipo=="S":
        primeros=Menu.objects.filter(parent=None).order_by('orden')
        for p in primeros:
            if VerificarHijos(p):
                primero={ 'router': '','children': []}
                primero['router']=p.router.replace('-','')
                for s in Menu.objects.filter(parent=p.id).order_by('orden'):
                    if VerificarHijos(s):
                        segundo={ 'router': '','children': []}
                        segundo['router']=s.router
                        for t in Menu.objects.filter(parent=s.id).order_by('orden'):
                            tercero=t.router
                            segundo['children'].append(tercero)
                        primero['children'].append(segundo)
                    else:
                        segundo=s.router
                        primero['children'].append(segundo)
                menus['children'].append(primero)
            else:
                primero=p.router
                menus['children'].append(primero)
        return Response([menus])
    elif usuario.perfil.tipo=="A" or usuario.perfil.tipo=="U" or usuario.perfil.tipo=="V":
        instancia=usuario.perfil.instancia
        perfil=Perfil.objects.get(usuario=usuario)
        lista=obtener_padres(perfil)
        disponibles=MenuInstancia.objects.filter(instancia=instancia,id__in=lista)
        primeros=disponibles.filter(parent=None).order_by('orden')
        for primer in primeros:
            if VerificarHijos(primer):
                primero={ 'router': '','children': []}
                nombrePrimero=primer.menu.router
                primero['router']=nombrePrimero.replace('-','')
                for s in disponibles.filter(parent=primer.id).order_by('orden'):
                    if VerificarHijos(s):
                        segundo={ 'router': '','children': []}
                        nombreSegundo=s.menu.router
                        segundo['router']=nombreSegundo
                        for t in disponibles.filter(parent=s.id).order_by('orden'):
                            tercero=t.menu.router
                            segundo['children'].append(tercero)
                        primero['children'].append(segundo)
                    else:
                        segundo=s.menu.router
                        primero['children'].append(segundo)
                menus['children'].append(primero)
            else:
                primero=primer.menu.router
                menus['children'].append(primero)
        return Response([menus])
    else:
        return Response(status=status.HTTP_403_FORBIDDEN)
# Funcion para obtener las columnas 
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def obtener_columnas(request):
    data=json.loads(request.body)
    columnas=[]
    try:
        for f in eval(data['value'])._meta.get_fields():
            JsonCol={
                'select': False,
                'title': f.name.capitalize(),
                'dataIndex': f.name,
                'align': 'left'
            }
            columnas.append(JsonCol)
        return Response(columnas)
    except ObjectDoesNotExist as e:
        return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def borrar_nota(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Notasdepago','borrar'):
        payload=json.loads(request.body)
        try:
            nota=NotasPago.objects.get(id=payload['idnota'])
            for obj in DetalleNotasPago.objects.filter(notapago=nota):
                proforma=Proforma.objects.get(id=obj.proforma.id)
                proforma.saldo_proforma=float(proforma.saldo_proforma)+float(obj.monto)
                proforma.save()
                obj.delete()
            nota.delete()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para actualizar las notas de pago
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualizar_nota(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Notasdepago','actualizar'):
        payload=json.loads(request.body)
        try:
            for obj in payload['data']:
                try:
                    if obj['monto'] > 0:
                        DetalleNotasPago.objects.filter(proforma=obj['proforma']).delete()
                        proforma=Proforma.objects.get(id=obj['proforma'])
                        perfil=Perfil.objects.get(usuario=request.user)
                        instancia=Instancia.objects.get(perfil=perfil.id)
                        nota_pago=NotasPago.objects.get(id=payload['idnota'])
                        detalle_nota=DetalleNotasPago(instancia=instancia,proforma=proforma,notapago=nota_pago,monto=obj['monto'],saldo_anterior=obj['saldo_anterior'])
                        detalle_nota.save()
                        proforma.saldo_proforma=proforma.saldo_proforma - detalle_nota.monto
                        proforma.save()
                except Exception as e:  
                    pass
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para actualizar los pedidos de la instancia
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualizar_pedido(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Pedido','actualizar'):
        payload=json.loads(request.body)
        try:
            pedido_id=Pedido.objects.get(id=payload['idpedido'])
            detashepedido=DetallePedido.objects.filter(pedido=pedido_id)
            id_dpedidos=[]
            total_proforma=0.0
            for dpedidos in detashepedido:
                id_dpedidos.append(dpedidos.id)
            for i in payload['data']:
                inventario=Inventario.objects.get(id=i['inventario'])
                if i['id']!=None:
                    indexpedido=None
                    for index,item in enumerate(detashepedido):
                        if item.id==i['id']:
                            indexpedido=index
                    cantidadanterior=detashepedido[indexpedido].cantidada
                    nuevodisponible=i['cantidada'] - cantidadanterior
                    inventario.disponible -= nuevodisponible
                    inventario.bloqueado += nuevodisponible
                perfil=Perfil.objects.get(usuario=request.user)
                precio_seleccionado=i['precio_seleccionado']
                producto=Producto.objects.get(id=i["producto"])
                instancia=Instancia.objects.get(perfil=perfil.id)
                cantidad=int(i["cantidada"])
                totalp=cantidad * precio_seleccionado
                precio_unidad=float(precio_seleccionado) # Calcular el precio de cada producto
                totalp=cantidad * float(precio_unidad) # Calcular el precio final segun la cantidad
                total_proforma+=float(totalp)
                pedido=pedido_id
                nuevo_componente=DetallePedido(lote=i["lote"],total_producto=totalp,precio_seleccionado=precio_seleccionado,instancia_id=instancia.id,pedido=pedido,cantidada=cantidad,producto=producto,inventario=inventario)
                nuevo_componente.save()
                if i['id']==None:
                    inventario.disponible=int(inventario.disponible) - cantidad
                    inventario.bloqueado=int(inventario.bloqueado)+cantidad
                inventario.save()
            pedido_id.total=total_proforma
            pedido_id.save()
            DetallePedido.objects.filter(id__in=id_dpedidos).delete()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para hacer la validacion de los pedidos
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def validar_pedido(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Pedido','actualizar'):
        payload=json.loads(request.body)
        try:
            pedido=Pedido.objects.get(id=payload['idpedido'])
            decision=payload['decision']
            detashepedido=DetallePedido.objects.filter(pedido=pedido)
            perfil=Perfil.objects.get(usuario=request.user)
            instancia=Instancia.objects.get(perfil=perfil.id)
            if payload['decision']=='Rechazado':
                pedido.estatus='C'
                pedido.save()
                for deta in detashepedido:
                    inventario=Inventario.objects.get(id=deta.inventario.id)
                    inventario.bloqueado=inventario.bloqueado - deta.cantidada
                    inventario.disponible=inventario.disponible+deta.cantidada
                    inventario.save()
                return Response(status=status.HTTP_200_OK)
            else:
                pedido.estatus='A'
                pedido.save()
                ## Se crea una nueva proforma,en base a los datos del pedido
                nueva_proforma=Proforma(pedido=pedido,instancia=instancia)
                nueva_proforma.cliente=pedido.cliente
                nueva_proforma.vendedor=pedido.vendedor
                nueva_proforma.empresa=pedido.empresa
                nueva_proforma.nombre_cliente=pedido.cliente.nombre
                nueva_proforma.identificador_fiscal=pedido.cliente.identificador
                nueva_proforma.direccion_cliente=pedido.cliente.ubicacion
                nueva_proforma.telefono_cliente=pedido.cliente.telefono
                nueva_proforma.precio_seleccionadoo=pedido.precio_seleccionadoo
                nueva_proforma.save()
                # Se crea el detalle de la proforma con la información asociada en el detalle pedido
                for deta in detashepedido:
                    nuevo_detalle=DetalleProforma(
                        proforma=nueva_proforma,
                        precio_seleccionado=deta.precio_seleccionado,
                        inventario=deta.inventario,
                        cantidada=deta.cantidada,
                        lote=deta.lote,
                        producto=deta.producto,
                        precio=deta.precio_seleccionado,
                        total_producto=deta.total_producto,
                        instancia=instancia
                    )
                    nuevo_detalle.save()
                    nueva_proforma.total += deta.total_producto
                    nueva_proforma.saldo_proforma=nueva_proforma.total
                    nueva_proforma.save()
                    inventario=Inventario.objects.get(id=deta.inventario.id)
                    inventario.bloqueado=inventario.bloqueado - deta.cantidada
                    inventario.save()
                return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para generar facturas
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def generar_factura(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Factura','escribir'):
        payload=json.loads(request.body)
        try:
            proforma=Proforma.objects.get(id=payload['idproforma'])
            detasheproforma=DetalleProforma.objects.filter(proforma=proforma)
            perfil=Perfil.objects.get(usuario=request.user)
            instancia=Instancia.objects.get(perfil=perfil.id)
            nueva_factura=Factura(proforma=proforma,instancia=instancia)
            nueva_factura.nombre_empresa=proforma.empresa.nombre
            nueva_factura.direccion_empresa= proforma.empresa.direccion_fiscal
            nueva_factura.id_cliente=proforma.cliente.id
            nueva_factura.nombre_cliente=proforma.cliente.nombre
            nueva_factura.identificador_fiscal=proforma.cliente.identificador
            nueva_factura.direccion_cliente=proforma.cliente.ubicacion
            nueva_factura.telefono_cliente=proforma.cliente.telefono
            nueva_factura.correo_cliente=proforma.cliente.mail
            nueva_factura.id_vendedor=proforma.cliente.id
            nueva_factura.nombre_vendedor=proforma.vendedor.nombre
            nueva_factura.telefono_vendedor=proforma.vendedor.telefono
            nueva_factura.impuesto=16
            nueva_factura.save()
            for deta in detasheproforma:
                    nuevo_detalle=DetalleFactura(
                        factura=nueva_factura,
                        inventario=deta.inventario,
                        inventario_fijo=deta.inventario,
                        cantidada=deta.cantidada,
                        lote=deta.lote,
                        fecha_vencimiento=deta.inventario.fecha_vencimiento,
                        producto=deta.producto,
                        producto_fijo=deta.producto.nombre,
                        precio=deta.precio_seleccionado,
                        total_producto=deta.total_producto,
                        instancia=instancia)
                    nuevo_detalle.save()
                    nueva_factura.subtotal += float( deta.total_producto)
                    nueva_factura.total += float( deta.total_producto)+(float( deta.total_producto) * (float(nueva_factura.impuesto) / 100))
                    nueva_factura.save()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para actualizar proformas 
@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualizar_proforma(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Proforma','actualizar'):
        payload=json.loads(request.body)
        try:
            proforma_id=Proforma.objects.get(id=payload['idproforma'])
            detasheproforma=DetalleProforma.objects.filter(proforma=proforma_id)
            id_proformas=[]
            total_proforma=0.0
            for dproformas in detasheproforma:
                id_proformas.append(dproformas.id)
            for i in payload['data']:
                inventario=Inventario.objects.get(id=i['inventario'])
                if i['id']!=None:
                    indexpedido=None
                    for index,item in enumerate(detasheproforma):
                        if item.id==i['id']:
                            indexpedido=index
                    cantidadanterior=detasheproforma[indexpedido].cantidada
                    nuevodisponible=i['cantidada'] - cantidadanterior
                    inventario.disponible -= nuevodisponible
                perfil=Perfil.objects.get(usuario=request.user)
                precio_seleccionado=i['precio_seleccionado']
                producto=Producto.objects.get(id=i["producto"])
                instancia=Instancia.objects.get(perfil=perfil.id)
                cantidad=int(i["cantidada"])
                totalp=cantidad * precio_seleccionado
                precio_unidad=float(precio_seleccionado) # Calcular el precio del producto en la venta
                totalp=cantidad * precio_unidad # Calcular el precio final del detalle segun la cantidad
                total_proforma += float(totalp)
                proforma=proforma_id
                nuevo_componente=DetalleProforma(proforma=proforma,lote=i["lote"],total_producto=totalp,precio_seleccionado=precio_seleccionado,precio=precio_unidad,instancia_id=instancia.id,cantidada=cantidad,producto=producto,inventario=inventario)
                nuevo_componente.save()
                if i['id']==None:
                    inventario.disponible=int(inventario.disponible) - cantidad
                inventario.save()
            proforma_id.total=total_proforma
            proforma_id.save()
            DetalleProforma.objects.filter(id__in=id_proformas).delete()
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return Response({'error': str(e)},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': e},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion para generar Excel de precios de productos
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def vista_xls(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Producto','leer'):
        response=HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition']='attachment; filename="productos.xls"'
        excel_wb=xlwt.Workbook(encoding='utf-8')
        excel_ws=excel_wb.add_sheet('Styling Data') # ws es Work Sheet
        i=0
        for m in Marca.objects.all().values():
            estilo=xlwt.easyxf('font: bold 1')
            excel_ws.write(i,0,'Marca:',estilo)
            excel_ws.write(i,1,m['nombre'])
            i=i+1
            excel_ws.write(i,0,'Codigo')
            excel_ws.write(i,1,'Producto')
            excel_ws.write(i,2,'Precio A')
            excel_ws.write(i,3,'Precio B')
            excel_ws.write(i,4,'Precio c')
            i=i+1
            for p in Producto.objects.filter(marca=m['id']).values():
                excel_ws.write(i,0,p['sku'])
                excel_ws.write(i,1,p['nombre'])
                excel_ws.write(i,2,p['precio_1'])
                excel_ws.write(i,3,p['precio_2'])
                excel_ws.write(i,4,p['precio_3'])
                i=i+1
        excel_wb.save(response)
        return response
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para guardar los pdfs de pedidos en el sistema operativo
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def guardar_pdf(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Proforma','actualizar'):
        try:
            data=request.data
            if not data:
                data['id']=1
            host=str(request.get_host())
            principal_url='http://%s'%(host)
            url=principal_url+'/apis/v1/pdf-proforma/%s'%(data['id'])
            response=requests.get(url)
            with open('proformas/proforma-%s.pdf'%data['id'],'wb') as f:
                f.write(response.content)
            return Response(True,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(False,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion tipo vista para obtener las ventas totales del mes actual y el anterior
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def ventas_totales(request):
    try:
        ahora=timezone.now()
        antes=timezone.datetime(month=ahora.month,year=ahora.year,day=1)
        total_actual=Proforma.objects.filter(fecha_proforma__range=(antes,ahora)).aggregate(cantidad=Sum('total'))
        mucho_antes=antes-timezone.timedelta(weeks=4)
        mucho_antes=mucho_antes.replace(day=1)
        total_anterior=Proforma.objects.filter(fecha_proforma__range=(mucho_antes,antes)).aggregate(cantidad=Sum('total'))
        total={'actual':{'fecha':antes,'total':total_actual,},'anterior':{'fecha':mucho_antes,'total':total_anterior,},}
        return Response(total,status=status.HTTP_200_OK)
    except Exception as e:
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo para obtener los permisos disponibles para la instancia
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def permisos_disponibles(request):
    perfil=Perfil.objects.get(usuario=request.user)
    if verificar_permiso(perfil,'Usuarios_y_permisos','leer'):
        try:
            perfil=Perfil.objects.get(usuario=request.user)
            menus=MenuInstancia.objects.filter(instancia=perfil.instancia)
            disponibles=[]
            for m in menus:
                if not menus.filter(parent=m) and m:
                    obj={}
                    obj['id']=m.id
                    obj['orden']=m.orden
                    try:
                        obj['menu_id']=m.menu.id
                    except:
                        pass
                    try:
                        obj['parent_id']=m.parent.id
                    except:
                        pass
                    try:
                        obj['nombreMenu']=m.menu.router
                    except:
                        pass
                    try:
                        obj['nombreParent']=m.parent.menu.router
                    except:
                        pass
                    disponibles.append(obj)
            return Response(data=disponibles,status=status.HTTP_200_OK)
        except Exception as e:
            return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        Response(status=status.HTTP_401_UNAUTHORIZED)
# Crear permisos
@api_view(["GET"])
@csrf_exempt
@permission_classes([IsAdminUser])
def ubop(request):
    try:
        perfil=Perfil.objects.get(usuario=request.user)
        menus=MenuInstancia.objects.filter(instancia=perfil.instancia)
        lista=[]
        for m in menus:
            if not menus.filter(parent=m):
                lista.append(m.id)
        permisos=MenuInstancia.objects.filter(id__in=lista)
        for p in permisos:
            Permiso.objects.create(instancia=perfil.instancia,menuinstancia=p,perfil=perfil,leer=True,escribir=True,borrar=True,actualizar=True)
        return Response('Hecho')
    except Exception as e:
        return Response('%s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo vista para obtener los usuarios y su informacion
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def perfiles_usuarios(request):
    perfil=Perfil.objects.get(usuario=request.user)
    instancia=perfil.instancia
    usuarios=User.objects.all() if perfil.tipo=='S' else User.objects.filter(instancia=instancia)
    disponibles=[]
    for u in usuarios:
        try:
            perfil=Perfil.objects.get(usuario=u)
        except:
            perfil=None
        usuario={'id':u.id,'email':u.email,'username':u.username,'permisos':[]}
        # Seteando el tipo de usuario
        usuario['tipo']=perfil.tipo if perfil else 'Sin perfil'
        if perfil:
            tipo=None
            tipo='Super' if perfil.tipo=='S' and not tipo else tipo
            tipo='Admin' if perfil.tipo=='A' and not tipo else tipo
            tipo='Usuario' if perfil.tipo=='U' and not tipo else tipo
            tipo='Vendedor' if perfil.tipo=='V' and not tipo else tipo
            usuario['nombreTipo']=tipo
        else:
            usuario['nombreTipo']='Sin perfil'
        # Escribiendo informacion del usuario
        usuario['perfil']=perfil.id if perfil else 'Sin perfil'
        usuario['instancia']=perfil.instancia.id if perfil else 'Sin perfil'
        usuario['nombreInstancia']=perfil.instancia.nombre if perfil else 'Sin perfil'
        usuario['activo']=perfil.activo if perfil else False
        if perfil:
            for p in Permiso.objects.filter(instancia=instancia,perfil=perfil):
                permiso={
                    'instancia_id':p.instancia.id,
                    'orden':p.menuinstancia.orden,
                    'menu_id':p.menuinstancia.menu.id,
                    'nombreMenu':p.menuinstancia.menu.router,
                    'perfil_id':p.perfil.id,
                    'leer':p.leer,
                    'escribir':p.escribir,
                    'borrar':p.borrar,
                    'actualizar':p.actualizar,
                }
                permiso['parent_id']=p.menuinstancia.parent.menu.id if p.menuinstancia.parent else None
                permiso['nombreParent']=p.menuinstancia.parent.menu.router if p.menuinstancia.parent else None
                usuario['permisos'].append(permiso)
        disponibles.append(usuario)
    return Response(disponibles,status=status.HTTP_200_OK)
# Funcion tipo vista para obtener los datos del usuario
@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def usuario_info(request):
    return Response(PerfilSerializer(Perfil.objects.get(usuario=request.user)).data,status=status.HTTP_200_OK)
@api_view(["POST", "GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def comision(request):
    data=request.data
    perfil=Perfil.objects.get(usuario=1)
    if verificar_permiso(perfil,'Comisiones','leer'):
        try:
            if not data:
                return Response("Error, Faltan los datos",status=status.HTTP_406_NOT_ACCEPTABLE)
            comision={'total_comision':0,'notas':[]}
            notas=NotasPago.objects.filter(instancia=perfil.instancia)
            notas_e=notas.filter(cliente=data['cliente'],fecha__month=data['mes'],fecha__year=data['año'])
            if len(notas_e)!=0:
                for n in notas_e:
                    nota={}
                    nota['id']=n.id
                    nota['cliente']=n.cliente.nombre
                    nota['cliente_id']=n.cliente.id
                    nota['comprobante']=n.comprobante
                    nota['descripcion']=n.descripcion
                    nota['fecha']=n.fecha
                    nota['total']=n.total
                    nota['detalles']=[]
                    for d in DetalleNotasPago.objects.filter(notapago__id=n.id):
                        detalle={}
                        detalle['id']=d.id
                        detalle['notapago_id']=d.notapago.id
                        detalle['proforma_id']=d.proforma.id
                        detalle['saldo_anterior']=d.saldo_anterior
                        detalle['monto']=d.monto
                        nota['detalles'].append(detalle)
                    comision['total_comision']+=n.total
                    comision['notas'].append(nota)
                comision['cliente_id']=data['cliente']
                comision['mes']=data['mes']
                comision['año']=data['año']
                return Response(comision,status=status.HTTP_200_OK)
            else:
                return Response("Error, No se encontraron notas de pago",status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response('Error, %s'%(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
# Funcion para obtener las instancias en las acciones
def obtener_instancia(perfil,instancia=None):
    return instancia if perfil.tipo=='S' and instancia else perfil.instancia.id
# Verificar que el usuario tenga permisos
def verificar_permiso(perfil,vista,accion):
    try:
        permiso=Permiso.objects.filter(instancia=perfil.instancia,menuinstancia__menu__router__exact=vista,perfil=perfil).first()
    except:
        return False
    if permiso:
        if accion=='leer':
            return permiso.leer
        elif accion=='escribir':
            return permiso.escribir
        elif accion=='actualizar':
            return permiso.actualizar
        elif accion=='borrar':
            return permiso.borrar
    return False
# Funcion para la primera carga del sistema
def crear_super_usuario(request):
    if Menu.objects.all().count()==0:
        for modelo in modelosMENU['modelos']:
            modulo=Modulo(nombre=modelo['router'])
            modulo.save()
            menu=Menu(router=modelo['router'],orden=modelo['orden'])
            menu.modulos=modulo
            menu.save()
            if modelo['parent']!=None:
                menu.parent=Menu.objects.get(router=modelo['parent'])
                menu.save()
    if Instancia.objects.all().count()==0:
        instancia=Instancia.objects.create(nombre="Primera",activo=True,multiempresa=True,vencimiento=None)
        for mod in Modulo.objects.all():
            instancia.modulos.add(mod)
        superuser=User.objects.create_user(username='super',password='super',is_staff=True, is_superuser=True)
        perfilS=Perfil(instancia=instancia,usuario_id=superuser,activo=True,avatar=None,tipo="S")
        perfilS.save()
        admin=User.objects.create_user(username='admin',password='admin')
        perfilA=Perfil(instancia=instancia,usuario=admin,activo=True,avatar=None,tipo="A")
        perfilA.save()
        usuario=User.objects.create_user(username='usuario',password='usuario')
        perfilU=Perfil(instancia=instancia,usuario=usuario,activo=True,avatar=None,tipo="U")
        perfilU.save()
        for m in Menu.objects.all().order_by('id'):
            menuinstancia=MenuInstancia(instancia_id=instancia,menu=m,orden=m.orden)
            menuinstancia.save()
            if m.parent!=None:
                menuinstancia.parent=MenuInstancia.objects.get(menu__id=m.parent.id)
                menuinstancia.save()
        return "Super creado"
    else:
        return "Ya existe un superusuario"
# Funcion para generar contraseñas
def generar_clave():
    lower=string.ascii_lowercase
    upper=string.ascii_uppercase
    numeros='1234567890'
    symbols='!$%&?*#@+='
    all=lower+upper+numeros+symbols
    temp=random.sample(all,16)
    return "".join(temp)
# Funcion para obtener el perfil del usuario
def obt_per(user):
    return Perfil.objects.get(usuario=user)
# Funcion para obtener la data de los permisos
def guardar_permisos(data,perfil_n=None,perfil_c=None,perfil=None):
    try:
        if perfil_c:
            if perfil:
                instancia=perfil.instancia if perfil else perfil_c.instancia
            if perfil_n:
                # Obtener datos para la creacion de permisos
                perfil_n=Perfil.objects.get(id=perfil_n)
                menus_i=MenuInstancia.objects.filter(instancia=instancia)
                permisos=Permiso.objects.filter(instancia=perfil_c.instancia,perfil=perfil_c)
                for per in data:
                    # Si se debe crear un menu, crearlo
                    padre=crear_menu(instancia,per['parent']) if perfil else None
                    menu=crear_menu(instancia,per['menu'],padre) if perfil else None
                    # Obtener menu
                    menu_i=menus_i.get(menu__router__exact=per['menu']) if not perfil else menu
                    # Verificar permiso del creador
                    permiso_c=permisos.filter(menuinstancia=menu_i).first()
                    if permiso_c:
                        if per['parent']:
                            # Obtener menu padre
                            menu_ip=menus_i.get(instancia=instancia,menu__router__exact=per['parent']) if not perfil else padre
                            crear_permiso(instancia,per,menu_ip,perfil_n,permiso_c)
                        crear_permiso(instancia,per,menu_i,perfil_n,permiso_c)
        return None
    except Exception as e:
        # Borrar datos creados
        try:
            Permiso.objects.filter(instancia=instancia,perfil=perfil).delete()
        except:
            pass
        return {'error':e}
# Funcion para crear/guardar los permisos
def crear_permiso(instancia,data,menu,perfil,creador):
    try:
        permiso=Permiso.objects.get(instancia=instancia,menuinstancia=menu,perfil=perfil)
    except:
        permiso=Permiso(instancia=instancia,menuinstancia=menu,perfil=perfil)
    permiso.leer=data['leer'] if creador.leer else False
    permiso.escribir=data['escribir'] if creador.escribir else False
    permiso.borrar=data['borrar'] if creador.borrar else False
    permiso.actualizar=data['actualizar'] if creador.actualizar else False
    permiso.save()
# Funcion para crear los admins por la nueva instancia
def crear_admin(data,super_p):
    try:
        user=User.objects.create(username=data['username'],email=data['email'],password=generar_clave())
        instancia=Instancia.objects.create(nombre=data['instancia'],activo=True,multiempresa=data['multiempresa'],vencimiento=data['vencimiento'])
        perfil=Perfil.objects.create(usuario=user,instancia=instancia,tipo='A')
        permisos=guardar_permisos(data['permisos'],perfil.id,super_p,perfil)
        if permisos:
            raise Exception('%s'%(permisos['error']))
        return Response(status=status.HTTP_201_CREATED)
    except Exception as e:
        try:
            user.delete()
        except:
            pass
        try:
            instancia.delete()
        except:
            pass
        try:
            perfil.delete()
        except:
            pass
        return Response('%s'%(e),status=status.HTTP_417_EXPECTATION_FAILED)
# Funcion para crear menu de la instancia
def crear_menu(instancia,menu,parent=None):
    menu=Menu.objects.get(router__exact=menu)
    menu_i=MenuInstancia.objects.create(instancia=instancia,menu=menu,parent=parent)
    return menu_i
# Funcion para obtener los menus superiores
def obtener_padres(perfil):
    menus=MenuInstancia.objects.filter(instancia=perfil.instancia)
    lista=[0]
    for p in Permiso.objects.filter(perfil=perfil):
        menu=menus.get(id=p.menuinstancia_id)
        encontrado=False
        if menu.parent:
            for l in lista:
                if l==menu.parent.id:
                    encontrado=True
                    break
        if not encontrado and menu.parent:
            lista.append(menu.parent.id)
        lista.append(menu.id)
    del lista[0]
    return lista