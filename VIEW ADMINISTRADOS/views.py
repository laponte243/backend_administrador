from django.db.models import Sum
from django.shortcuts import render
from .serializers import *
from .models import *
from django.contrib.auth.models import User
from rest_framework import viewsets, generics, request, mixins, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from django_filters import rest_framework as filters
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.utils import json
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core import serializers
from datetime import datetime
import csv


@permission_classes([IsAuthenticated])
class UsuariosViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = UserSerializer

@permission_classes([IsAuthenticated])
class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoriaproducto.objects.all()
    serializer_class = CategoriaSerializer

@permission_classes([IsAuthenticated])
class MarcadelproductoViewSet(viewsets.ModelViewSet):
    queryset = MarcadelProducto.objects.all()
    serializer_class = MarcadelproductoSerializer

@permission_classes([IsAuthenticated])
class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer

@permission_classes([IsAuthenticated])
class MarcaViewSet(viewsets.ModelViewSet):
    queryset = Marcadecarro.objects.all()
    serializer_class = MarcadecarroSerializer

@permission_classes([IsAuthenticated])
class ModeloViewSet(viewsets.ModelViewSet):
    queryset = Modelocarro.objects.all()
    serializer_class = ModelodecarroSerializer

@permission_classes([IsAuthenticated])
class ClientesViewSet(viewsets.ModelViewSet):
    queryset = Clientes.objects.all()
    serializer_class = ClientesSerializer


@permission_classes([IsAuthenticated])
class OrdenViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Ordendetrabajo.objects.all()
    serializer_class = ordenSerializer

class DetalleordenViewSet(viewsets.ModelViewSet):
    serializer_class = orden_detalleSerializer

    def get_queryset(self):
        queryset = ordendetrabajo_detalle.objects.all()
        ordendetrabajo = self.request.query_params.get('ordendetrabajo', None)
        if ordendetrabajo is not None:
            queryset = queryset.filter(ordendetrabajo=ordendetrabajo)
        return queryset


@api_view(["POST"])
@csrf_exempt
@permission_classes([AllowAny])
def get_id(request):
    data = json.loads(request.body)
    try:
        uid = User.objects.get(username=data['username'])
        return JsonResponse({'id': uid.id}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




@api_view(["POST"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def sumatotal(request):
    data = json.loads(request.body)
    print(data)
    try:
        registro = Inventario.objects.get(id=data['id'])
        registro.cantidad = registro.cantidad + int(data['cantidadsum'])
        print(registro.cantidad)
        registro.save()
        return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        
@api_view(["POST"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def restatotal(request):
    data = json.loads(request.body)
    print(data)
    try:
        registro = Inventario.objects.get(id=data['id'])
        registro.cantidad = registro.cantidad - int(data['cantidadsum'])
        print(registro.cantidad)
        registro.save()
        return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def filtrar(request):
    data = json.loads(request.body)
    print(data)
    try:
        modelocarro = Modelocarro.objects.get(id=data['modelocarro'])
        tipoproducto = str(data['tipoproducto'])
        origen = str(data['origen'])
        
       
        objetos = Inventario.objects.all()

        if modelocarro != 'todos':
            objetos = objetos.filter(modelocarro__id=modelocarro.id)  
        if tipoproducto !=  'todos':
            objetos = objetos.filter(tipoproducto=tipoproducto)
        if origen !=  'todos':
            objetos = objetos.filter(origen=origen)
        dataretorno = []
        print(objetos)
        for obj in objetos:
            modelos = ''
            marcas = ''
            for modelo in obj.modelocarro.all():
                modelos += modelo.descripcion+ ' '
            for marca in obj.marcacarro.all():
                marcas += marca.descripcion+ ' '
            dataretorno.append({  
                                'id': obj.id,
                                'tipoproducto': obj.tipoproducto,  
                                'marcaproducto': obj.marcaproducto,
                                'codigoproducto': obj.codigoproducto,  
                                'modelocarro': modelos,
                                'marcacarro': marcas,  
                                'origen': obj.origen,  
                                'cantidad': obj.cantidad,  
                                'preciocompra': obj.preciocompra,  
                                'precioventa': obj.precioventa,  
                                'status': obj.status,
                                'created_at': str(obj.created_at),
                                'fechacarro': obj.fechacarro,
                                'observacion': obj.observacion,
                                'fechacarro': obj.fechacarro,
                                'fechacarro_max': obj.fechacarro_max,
                                })
        return HttpResponse(json.dumps(dataretorno), content_type="application/json")
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(e)
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def actualiza_orden(request, id_orden):
    payload = json.loads(request.body)
    try:
        orden_id = Ordendetrabajo.objects.get(id=id_orden)
        data = payload['item']
        cliente = Clientes.objects.get(id=data['cliente'])
        modelovehiculo = Modelocarro.objects.get(id=data['modelovehiculo'])
        marcavehiculo = Marcadecarro.objects.get(id=data['marcavehiculo'])
        orden_id.cliente=cliente
        orden_id.modelovehiculo=modelovehiculo
        orden_id.marcavehiculo=marcavehiculo
        orden_id.añovehiculo=data['añovehiculo']
        orden_id.placa=data['placa']
        orden_id.kilometraje=data['kilometraje']
        orden_id.estatus=data['estatus']
        orden_id.precio_manodeobra=data['precio_manodeobra']
        orden_id.save()
        orden = Ordendetrabajo.objects.get(id=id_orden)
        serializer = ordenSerializer(orden)
        ordendetrabajo_detalle.objects.filter(ordendetrabajo=orden).delete()
        for i in payload['tablaComponentesItems']:
            producto = Categoriaproducto.objects.get(id=i["id"])
            cantidad = int(i["cantidad"])
            precio_compra = float(i["precio_compra"])
            precio_venta = float(i["precio_venta"])
            nuevo_componente = ordendetrabajo_detalle(precio_venta=precio_venta,precio_compra=precio_compra,cantidad_producto=cantidad,ordendetrabajo=orden,producto=producto)
            nuevo_componente.save()
        return JsonResponse({'orden': serializer.data}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(e)
        return JsonResponse({'error': e}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def eliminar_producto(request, id_orden):
    try:
        orden_id = Ordendetrabajo.objects.get(id=id_orden)
        detalle_orden = ordendetrabajo_detalle.objects.filter(ordendetrabajo=orden_id)
        detalle_orden.delete()
        orden_id.delete()
        return JsonResponse({'success': 'Registro eliminado'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return JsonResponse({'error': 'Something terrible went wrong'}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django_renderpdf.views import PDFView
from django.contrib.auth.mixins import LoginRequiredMixin
class detalle_pdf(PDFView):
    template_name = 'orden_trabajo.html'
    allow_force_html = True
    def get_context_data(self, *args, **kwargs):
        """Pass some extra context to the template."""
        context = super().get_context_data(*args, **kwargs)
        totalcosto = 0
        total = 0
        orden = Ordendetrabajo.objects.get(id=kwargs['id_orden'])
        detalle = ordendetrabajo_detalle.objects.filter(ordendetrabajo=orden)
        for producto in detalle:
            total += producto.precio_venta * producto.cantidad_producto
            totalcosto += producto.precio_compra * producto.cantidad_producto
        total += orden.precio_manodeobra 
        totalcosto = total - totalcosto
        context['orden'] = orden
        context['detalle'] = detalle
        context['utilidad'] = totalcosto
        return context


class nota_entrega(PDFView):
    template_name = 'nota_entrega.html'
    allow_force_html = True
    def get_context_data(self, *args, **kwargs):
        """Pass some extra context to the template."""
        context = super().get_context_data(*args, **kwargs)
        total = 0
        totalcosto = 0
        orden = Ordendetrabajo.objects.get(id=kwargs['id_orden'])
        detalle = ordendetrabajo_detalle.objects.filter(ordendetrabajo=orden)
        for producto in detalle:
            total += producto.precio_venta * producto.cantidad_producto
            totalcosto += producto.precio_compra * producto.cantidad_producto
        total += orden.precio_manodeobra 
        totalcosto = total - totalcosto
        context['orden'] = orden
        context['detalle'] = detalle
        context['total'] = total
        context['utilidad'] = totalcosto
        return context



class inventario(PDFView):
    template_name = 'inventario.html'
    allow_force_html = True
    def get_context_data(self, *args, **kwargs):
      """Pass some extra context to the template."""
      context = super().get_context_data(*args, **kwargs)
      inventario = Inventario.objects.all()
      context['inventario'] = inventario
      return context






@api_view(["GET"])
@csrf_exempt
@permission_classes([IsAuthenticated])
def anios(request):
    try:
        dataretorno = []
        for obj in range(1900, int(datetime.today().year) + 5):
            dataretorno.append({  
                                'año': obj,
                                })
        return JsonResponse({'año': dataretorno}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return JsonResponse({'error': 'Something terrible went wrong'}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Inventario.csv"'

    writer = csv.writer(response)
    writer.writerow(['Codigo','Tipo de producto', 'Marca del producto', 'Marca del carro','Modelo del vechiculo', 'Fecha del vehiculo', 'Fecha maxima del vehiculo', 'Nacional o importado', 'Total en existencia', 'Precio de compra', 'Precio de venta', 'Disponibilidad', 'Fecha de creación', 'Observacion'])
    registros   = Inventario.objects.all()
    for registro in registros:
        modelos = ''
        marcas = ''
        for modelo in registro.modelocarro.all():
            modelos += modelo.descripcion+ ' '
        for marca in registro.marcacarro.all():
                marcas += marca.descripcion+ ' '
        writer.writerow([registro.codigoproducto, registro.tipoproducto, registro.marcaproducto, marcas , modelos, registro.fechacarro, registro.fechacarro_max, registro.origen, registro.cantidad, registro.preciocompra, registro.precioventa, registro.status, registro.created_at, registro.observacion])

    return response
