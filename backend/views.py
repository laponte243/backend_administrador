# Importes de Rest framework
from email import header
from urllib import response
from numpy import indices
from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.utils import json
from django_filters.rest_framework import DjangoFilterBackend
# Importes de Django
from django.apps import apps
from django.db.models import Count, Q, Sum
from django.contrib.auth import login
from django.core import serializers as sr
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse, request
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
# Raiz
from .serializers import *
from .models import *
from .menu import *
# Recuperar contraseña
from knox.views import LoginView as KnoxLoginView
from django.conf import settings
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django_rest_passwordreset.signals import reset_password_token_created
from django.urls import reverse
from django.template.loader import render_to_string
# Pandas
import pandas as pd
import csv
import xlwt
import requests

# Utiles
""" Reseteo de contraseña """
@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):

    RESET_PASSWORD_ROUTE = getattr(settings, "RESET_PASSWORD_ROUTE", None)
    # email_plaintext_message = "{}?token={}".format(reverse('password_reset:reset-password-request'), reset_password_token.key)
    # import html message.html file
    context = ({"url": RESET_PASSWORD_ROUTE +
               '#/passwordset?token=' + reset_password_token.key})
    resetPasswordTemplate = 'user_reset_password.html'
    reset_password_message = render_to_string(resetPasswordTemplate, context)
    # send email
    subject, from_email, to = "Password Reset for {title}".format(
        title="DataVisualizer"), 'noreply@somehost.local', reset_password_token.user.email
    text_content = ''
    html_content = reset_password_message
    msg = EmailMessage(subject, html_content, from_email, [to])
    msg.content_subtype = "html"  # Main content is now text/html
    msg.send()

""" Acceso de KNOX """
class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        # return super(LoginView, self).post(request, format=None)
        temp_list = super(LoginView, self).post(request, format=None)
        temp_list.data["user_id"] = user.id
        temp_list.data["first_name"] = user.first_name
        temp_list.data["last_name"] = user.last_name
        temp_list.data["last_login"] = user.last_login
        return Response({"data": temp_list.data})

""" Vista creada para el modelo de Group """
class GroupVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupMSerializer

""" Vista creada para el modelo de Permission """
class PermissionVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    queryset = Permission.objects.all().order_by('name')
    serializer_class = PermissionMSerializer

""" Vista modificada para el modelo mixim de User """
class UserVS(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = UsuarioMSerializer

    """ Motodo de crear no permitido """
    def create(self, request):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    """ Metodo de leer """
    def get_queryset(self):
        if (self.request.user.perfil.tipo == 'S'):
            return User.objects.all()
        elif (self.request.user.perfil.tipo == 'A'):
            instancia = Perfil.objects.get(usuario=self.request.user).instancia
            return User.objects.filter(perfil__instancia=instancia).exclude(perfil__tipo='A')
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

    """ Metodo de actualizar no creada """
    # def update(self): Actualizacion original

    """ Metodo de eliminar """
    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        objeto = self.get_object()
        # Super
        if (perfil.tipo == 'S'):
            Perfil.objects.get(usuario=self.request.data.id).delete()
            objeto.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        # Admin
        elif (perfil.tipo == 'A'):
            # Verificar que el usuario a borrar no sea Staff, y este en la misma instancia desde donde se hace la peticion
            if (objeto.perfil.tipo != 'S' and objeto.perfil.tipo != 'A' and str(objeto.perfil.instancia.id) == str(perfil.instancia.id)):
                Perfil.objects.get(usuario=self.request.data.id).delete()
                objeto.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
        # Usuario/Vendedor
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

""" Vista del modelo Modulo """
class ModuloVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ModuloSerializer

    """ Metodo de crear no disponible """
    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    """ Metodo de leer """
    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        # Super
        if (perfil.tipo == 'S'):
            return Modulo.objects.all().order_by('nombre')
        # Admin
        if (perfil.tipo == 'A'):
            modulos = []
            for m in perfil.instancia.modulo:
                modulos.append(m)
            return modulos
        # Usuario/Vendedor
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    """ Metodo de actualizar no disponible """
    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    """ Metodo de eliminar no disponible """
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

""" Vista para el modelo Menu """
class MenuVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [TokenAuthentication]
    serializer_class = MenuSerializer

    """ Metodo de crear no disponible """
    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    """ Metodo de leer """
    def get_queryset(self):
        # Verificar si existen los menus
        menus = Menu.objects.all()
        if (menus.count() == 0):
            for m in modelosMENU['modelos']:
                menu = Menu(router=m['router'], orden=m['orden'])
                menu.save()
                if (m['parent'] != None):
                    menu.parent = Menu.objects.get(id=m['parent'])
                    menu.save()
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return menus
        else:
            return None

    def update(self, request, *args, **kwargs):
       perfil = Perfil.objects.get(usuario=self.request.user)
       if (perfil.tipo == 'S'):
           partial = True  # Here I change partial to True
           instance = self.get_object()
           serializer = self.get_serializer(
               instance, data=request.data, partial=partial)
           serializer.is_valid(raise_exception=True)
           self.perform_update(serializer)
           return Response(serializer.data, status=status.HTTP_200_OK)
       else:
           return Response(status=status.HTTP_403_FORBIDDEN)

    """ Metodo de eliminar no disponible """
    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

# Instancia

""" """
class InstanciaVS(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser, IsAuthenticated]
    serializer_class = InstanciaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S' and self.request.user.is_superuser == True):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif(perfil.tipo == 'S'):
            return JsonResponse({"error": "Your profile or user has deactivated being superuser"}, status=status.HTTP_403_FORBIDDEN)
        else:
            return JsonResponse({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Instancia.objects.all().order_by('nombre')
        else:
            return None

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Forbidden, user no have permissions'}, status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        return Response(False, status=status.HTTP_403_FORBIDDEN)

""" """
class MenuInstanciaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = MenuInstanciaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return MenuInstancia.objects.all().order_by('id')
        elif (perfil.tipo == 'A'):
            return MenuInstancia.objects.filter(instancia=perfil.instancia).order_by('id')
        else:
            return JsonResponse({"error": "Forbidden, can't you see", }, status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)  # Change

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)  # Change
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)  # Change

""" """
class PerfilVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = PerfilSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Perfil.objects.all().order_by('usuario')
        elif (perfil.tipo == 'A'):
            return Perfil.objects.filter(instancia=perfil.instancia).order_by('usuario')
        else:
            return Perfil.objects.filter(id=perfil.id).order_by('usuario')

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=datos, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            # Change
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            try:
                objeto = Perfil.objects.get(usuario=self.request.user)
                objeto.avatar = request.data['avatar']
                self.perform_update(objeto)
                return Response(objeto, status=status.HTTP_200_OK)
            except:
                return Response({'error': 'Problem with user or selected avatar'}, status=status.HTTP_401_UNAUTHORIZED)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)  # Change
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)  # Change

""" """
class PermisoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = PermisoSerializer

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Permiso.objects.all().order_by('id')
        elif (perfil.tipo == 'A'):
            return Permiso.objects.filter(instancia=perfil.instancia).order_by('perfil')
        else:
            return Permiso.objects.filter(perfil=perfil.id)

    def update(self):
        # Change status
        return JsonResponse({"error": "No authorized"}, status=status.HTTP_403_FORBIDDEN)

# Empresa

""" """
class EmpresaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = EmpresaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Empresa.objects.all().order_by('nombre')
        else:
            return Empresa.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class ContactoEmpresaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ContactoEmpresaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return ContactoEmpresa.objects.all().order_by('nombre')
        else:
            return ContactoEmpresa.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class ConfiguracionPapeleriaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ConfiguracionPapeleriaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return ConfiguracionPapeleria.objects.all().order_by('valor', 'empresa')
        else:
            return ConfiguracionPapeleria.objects.filter(instancia=perfil.instancia).order_by('valor', 'empresa')

# Inventario

""" """
class TasaConversionVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = TasaConversionSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return TasaConversion.objects.all().order_by('-id')
        else:
            return TasaConversion.objects.filter(instancia=perfil.instancia)

""" """
class ImpuestosVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ImpuestosSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Impuestos.objects.all().order_by('nombre')
        else:
            return Impuestos.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class MarcaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = MarcaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Marca.objects.all().order_by('nombre')
        else:
            return Marca.objects.filter(instancia=perfil.instancia).order_by('nombre')


# class UnidadVS(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [TokenAuthentication]
#     queryset = Unidad.objects.all().order_by('nombre')
#     serializer_class = UnidadSerializer

#     def create(self, request):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         datos = request.data
#         datos['instancia'] = perfil.instancia.id
#         if (perfil.tipo == 'S'):
#             serializer = self.get_serializer(data=datos)
#             serializer.is_valid(raise_exception=True)
#             self.perform_create(serializer)
#             headers = self.get_success_headers(serializer.data)
#             return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#         elif (perfil.tipo == 'A'):
#             datos = request.data
#             datos['instancia'] = perfil.instancia.id
#             serializer = self.get_serializer(data=datos)
#             serializer.is_valid(raise_exception=True)
#             self.perform_create(serializer)
#             headers = self.get_success_headers(serializer.data)
#             return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#         else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def update(self, request, *args, **kwargs):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         if (perfil.tipo == 'S'):
#             partial = True  # Here I change partial to True
#             instance = self.get_object()
#             serializer = self.get_serializer(
#                 instance, data=request.data, partial=partial)
#             serializer.is_valid(raise_exception=True)
#             self.perform_update(serializer)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         else:
#             if (str(request.data['instancia']) == str(perfil.instancia.id)):
#                 partial = True  # Here I change partial to True
#                 instance = self.get_object()
#                 serializer = self.get_serializer(
#                     instance, data=request.data, partial=partial)
#                 serializer.is_valid(raise_exception=True)
#                 self.perform_update(serializer)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
#             else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def destroy(self, request, *args, **kwargs):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         instance = self.get_object()
#         if (perfil.tipo == 'S'):
#             instance.delete()
#             return Response(status=status.HTTP_204_NO_CONTENT)
#         else:
#             if (str(instance.instancia.id) == str(perfil.instancia.id)):
#                 instance.delete()
#                 return Response(status=status.HTTP_204_NO_CONTENT)
#             else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def get_queryset(self):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         if (perfil.tipo == 'S'):
#             return Unidad.objects.all().order_by('nombre')
#         else:
#             return Unidad.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class ProductoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ProductoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['servicio', 'menejo_inventario', 'activo']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        if (perfil.tipo == 'S'):
            datos['instancia'] = str(perfil.instancia.id)
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            # for lp in ListaPrecio.objects.filter(instancia_id=perfil.instancia.id):
            #     pro = Producto.objects.get(id=serializer.data['id'])
            #     costo_final = pro.costo + (pro.costo * (lp.porcentaje / 100))
            #     detalle = DetalleListaPrecio(
            #         instancia=perfil.instancia, listaprecio=lp, producto=pro, precio=costo_final)
            #     detalle.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos['instancia'] = str(perfil.instancia.id)
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            # for lp in ListaPrecio.objects.filter(instancia_id=perfil.instancia.id):
            #     pro = Producto.objects.get(id=serializer.data['id'])
            #     costo_final = pro.costo + (pro.costo * (lp.porcentaje / 100))
            #     detalle = DetalleListaPrecio(
            #         instancia=perfil.instancia, listaprecio=lp, producto=pro, precio=costo_final)
            #     detalle.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            # for lp in DetalleListaPrecio.objects.filter(instancia_id=perfil.instancia.id, producto_id=serializer.data['id']):
            #     costo_final = serializer.data['costo'] + (
            #         serializer.data['costo'] * (lp.listaprecio.porcentaje / 100))
            #     lp.precio = costo_final
            #     lp.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                # for lp in DetalleListaPrecio.objects.filter(instancia_id=perfil.instancia.id, producto_id=serializer.data['id']):
                #     costo_final = serializer.data['costo'] + \
                #         (serializer.data['costo'] * (lp.porcentaje / 100))
                #     lp.precio = costo_final
                #     lp.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Producto.objects.all().order_by('id')
        else:
            return Producto.objects.filter(instancia=perfil.instancia).order_by('id')

""" """
class ProductoImagenVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    queryset = ProductoImagen.objects.all().order_by('producto', 'principal')
    serializer_class = ProductoImagenSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return ProductoImagen.objects.all().order_by('producto', 'principal')
        else:
            return ProductoImagen.objects.filter(instancia=perfil.instancia).order_by('producto', 'principal')

""" """
class AlmacenVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = AlmacenSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Almacen.objects.all().order_by('nombre')
        else:
            return Almacen.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class MovimientoInventarioVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = MovimientoInventarioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['producto', 'almacen']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            objeto = MovimientoInventario.objects.filter(
                instancia_id=datos['instancia'], producto_id=datos['producto'], almacen_id=datos['almacen'])
            if objeto.count() > 0:
                    Inventario.objects.create(instancia_id=datos['instancia'], producto_id=datos['producto'], almacen_id=datos['almacen'],
                                              disponible=datos['cantidad_recepcion'], bloqueado=0, lote=datos['lote'], fecha_vencimiento=datos['fecha_vencimiento'])
            else:
                Inventario.objects.create(instancia_id=datos['instancia'], producto_id=datos['producto'], almacen_id=datos['almacen'],
                                          disponible=datos['cantidad_recepcion'], bloqueado=0, lote=datos['lote'], fecha_vencimiento=datos['fecha_vencimiento'])
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return MovimientoInventario.objects.all().order_by('id')
        else:
            return MovimientoInventario.objects.filter(instancia=perfil.instancia).order_by('lote')

""" """
class DetalleInventarioVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = InventarioSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['producto', 'almacen']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Inventario.objects.all().order_by('almacen', 'producto')
        else:
            return Inventario.objects.filter(instancia=perfil.instancia).order_by('almacen', 'producto')


@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def Inven(request):
    perfil = Perfil.objects.get(usuario=request.user)
    if perfil:
        objeto_inventario = Inventario.objects.filter(instancia=perfil.instancia).values(
            'almacen', 'almacen__nombre', 'producto', 'producto__nombre').annotate(sum_disponible=Sum('disponible'), sum_bloqueado=Sum('bloqueado'))
        return Response(objeto_inventario, status=status.HTTP_200_OK)

# ventas

""" """
class VendedorVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = VendedorSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activo']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Vendedor.objects.all().order_by('nombre')
        else:
            return Vendedor.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class ClienteVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ClienteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['activo']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Cliente.objects.all().order_by('nombre')
        else:
            return Cliente.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class ContactoClienteVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ContactoClienteSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return ContactoCliente.objects.all().order_by('nombre')
        else:
            return ContactoCliente.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class PedidoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = PedidoSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Pedido.objects.all()
        else:
            return Pedido.objects.filter(instancia=perfil.instancia)

""" """
class DetallePedidoVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = DetallePedidoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pedido']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            inventario = Inventario.objects.get(id=instance.inventario.id)
            inventario.bloqueado = inventario.bloqueado - instance.cantidada
            inventario.disponible = inventario.disponible + instance.cantidada
            inventario.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return DetallePedido.objects.all()
        else:
            return DetallePedido.objects.filter(instancia=perfil.instancia)

""" """
class ProformaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ProformaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            DetalleProforma.objects.filter(proforma=instance.id).delete()
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                DetalleProforma.objects.filter(proforma=instance.id).delete()
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Proforma.objects.all()
        else:
            return Proforma.objects.filter(instancia=perfil.instancia)

""" """
class DetalleProformaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = DetalleProformaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['proforma']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            inventario = Inventario.objects.get(id=instance.inventario.id)
            inventario.disponible = inventario.disponible + instance.cantidada
            inventario.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return DetalleProforma.objects.all()
        else:
            return DetalleProforma.objects.filter(instancia=perfil.instancia)

""" """
class FacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = FacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Factura.objects.all()
        else:
            return Factura.objects.filter(instancia=perfil.instancia)

""" """
class DetalleFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = DetalleFacturaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['factura']

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return DetalleFactura.objects.all()
        else:
            return DetalleFactura.objects.filter(instancia=perfil.instancia)

""" """
# class ListaPrecioVS(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [TokenAuthentication]
#     serializer_class = ListaPrecioSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['activo']

#     def create(self, request):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         datos = request.data
#         if (perfil.tipo == 'S'):
#             datos['instancia'] = str(perfil.instancia.id)
#             if (datos['predeterminada'] == True):
#                 if ListaPrecio.objects.filter(predeterminada=True).exists():
#                     error = 'Ya existe una lista predeterminada'
#                     return Response(error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             serializer = self.get_serializer(data=datos)
#             serializer.is_valid(raise_exception=True)
#             self.perform_create(serializer)
#             headers = self.get_success_headers(serializer.data)
#             productos = Producto.objects.filter(
#                 instancia_id=perfil.instancia.id)
#             for o in productos:
#                 costo_final = o.costo + \
#                     (o.costo * (serializer.data['porcentaje'] / 100))
#                 listad = DetalleListaPrecio.objects.create(
#                     instancia_id=datos['instancia'], producto=o, precio=costo_final, listaprecio_id=serializer.data['id'])
#             return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#         elif (perfil.tipo == 'A'):
#             datos['instancia'] = str(perfil.instancia.id)
#             if datos['predeterminada'] == True:
#                 if ListaPrecio.objects.filter(predeterminada=True).exists():
#                     error = 'Ya existe una lista predeterminada'
#                     return Response(error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             serializer = self.get_serializer(data=datos)
#             serializer.is_valid(raise_exception=True)
#             self.perform_create(serializer)
#             headers = self.get_success_headers(serializer.data)
#             return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#         else:
#             return Response(status=status.HTTP_403_FORBIDDEN)

#     def update(self, request, *args, **kwargs):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         datos = request.data
#         if (perfil.tipo == 'S'):
#             datos['instancia'] = str(perfil.instancia.id)
#             if datos['predeterminada'] == True:
#                 if ListaPrecio.objects.filter(predeterminada=True).exclude(id=kwargs['pk']).exists():
#                     error = 'Ya existe una lista predeterminada'
#                     return Response(error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             partial = True  # Here I change partial to True
#             instance = self.get_object()
#             serializer = self.get_serializer(
#                 instance, data=request.data, partial=partial)
#             serializer.is_valid(raise_exception=True)
#             self.perform_update(serializer)
#             DetalleListaPrecio.objects.filter(
#                 instancia_id=perfil.instancia.id, listaprecio=serializer.data['id']).delete()
#             productos = Producto.objects.filter(
#                 instancia_id=perfil.instancia.id)
#             for o in productos:
#                 costo_final = o.costo + \
#                     (o.costo * (serializer.data['porcentaje'] / 100))
#                 listad = DetalleListaPrecio.objects.create(
#                     instancia_id=datos['instancia'], producto=o, precio=costo_final, listaprecio_id=serializer.data['id'])
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         else:
#             if (str(request.data['instancia']) == str(perfil.instancia.id)):
#                 datos['instancia'] = str(perfil.instancia.id)
#                 if datos['predeterminada'] == True:
#                     if ListaPrecio.objects.filter(predeterminada=True).exists():
#                         return Response({'error': 'Ya existe una lista predeterminada'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#                 partial = True  # Here I change partial to True
#                 instance = self.get_object()
#                 serializer = self.get_serializer(
#                     instance, data=request.data, partial=partial)
#                 serializer.is_valid(raise_exception=True)
#                 self.perform_update(serializer)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
#             else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def destroy(self, request, *args, **kwargs):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         instance = self.get_object()
#         if (perfil.tipo == 'S'):
#             instance.delete()
#             return Response(status=status.HTTP_204_NO_CONTENT)
#         else:
#             if (str(instance.instancia.id) == str(perfil.instancia.id)):
#                 instance.delete()
#                 return Response(status=status.HTTP_204_NO_CONTENT)
#             else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def get_queryset(self):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         listas = ListaPrecio.objects.filter(
#             instancia=perfil.instancia, predeterminada=True)
#         if listas.exists() and listas.count() > 1:
#             for l in listas:
#                 l.predeterminada = False
#                 l.save()
#             lista = ListaPrecio.objects.filter(
#                 instancia=perfil.instancia, activo=True).first()
#             lista.predeterminada = True
#             lista.save()
#         if (perfil.tipo == 'S'):
#             return ListaPrecio.objects.all().order_by('id')
#         else:
#             return ListaPrecio.objects.filter(instancia=perfil.instancia).order_by('id')

# """ """
# class DetalleListaPrecioVS(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [TokenAuthentication]
#     serializer_class = DetalleListaPrecioSerializer
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['listaprecio', 'producto__activo']

#     def create(self, request):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         datos = request.data
#         if (perfil.tipo == 'S'):
#             _mutable = datos._mutable
#             datos._mutable = True
#             datos['instancia'] = str(perfil.instancia.id)
#             datos._mutable = _mutable
#             serializer = self.get_serializer(data=datos)
#             serializer.is_valid(raise_exception=True)
#             self.perform_create(serializer)
#             headers = self.get_success_headers(serializer.data)
#             return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#         elif (perfil.tipo == 'A'):
#             _mutable = datos._mutable
#             datos._mutable = True
#             datos['instancia'] = str(perfil.instancia.id)
#             datos._mutable = _mutable
#             serializer = self.get_serializer(data=datos)
#             serializer.is_valid(raise_exception=True)
#             self.perform_create(serializer)
#             headers = self.get_success_headers(serializer.data)
#             return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
#         else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def update(self, request, *args, **kwargs):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         if (perfil.tipo == 'S'):
#             partial = True  # Here I change partial to True
#             instance = self.get_object()
#             serializer = self.get_serializer(
#                 instance, data=request.data, partial=partial)
#             serializer.is_valid(raise_exception=True)
#             self.perform_update(serializer)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         else:
#             if (str(request.data['instancia']) == str(perfil.instancia.id)):
#                 _mutable = datos._mutable
#                 datos._mutable = True
#                 datos['instancia'] = str(perfil.instancia.id)
#                 datos._mutable = _mutable
#                 partial = True  # Here I change partial to True
#                 instance = self.get_object()
#                 serializer = self.get_serializer(
#                     instance, data=request.data, partial=partial)
#                 serializer.is_valid(raise_exception=True)
#                 self.perform_update(serializer)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
#             else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def destroy(self, request, *args, **kwargs):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         instance = self.get_object()
#         if (perfil.tipo == 'S'):
#             instance.delete()
#             return Response(status=status.HTTP_204_NO_CONTENT)
#         else:
#             if (str(instance.instancia.id) == str(perfil.instancia.id)):
#                 instance.delete()
#                 return Response(status=status.HTTP_204_NO_CONTENT)
#             else:
#                 return Response(status=status.HTTP_403_FORBIDDEN)

#     def get_queryset(self):
#         perfil = Perfil.objects.get(usuario=self.request.user)
#         if (perfil.tipo == 'S'):
#             return DetalleListaPrecio.objects.all().order_by('producto', '-precio')
#         else:
#             return DetalleListaPrecio.objects.filter(instancia=perfil.instancia).order_by('producto', '-precio')

""" """
class ImpuestosFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ImpuestosFacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return ImpuestosFactura.objects.all().order_by('nombre')
        else:
            return ImpuestosFactura.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class NumerologiaFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = NumerologiaFacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return NumerologiaFactura.objects.all().order_by('tipo', 'valor')
        else:
            return NumerologiaFactura.objects.filter(instancia=perfil.instancia).order_by('tipo', 'valor')

""" """
class NotaFacturaVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = NotaFacturaSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return NotaFactura.objects.all().order_by('venta')
        else:
            return NotaFactura.objects.filter(instancia=perfil.instancia).order_by('venta')

# Compras

""" """
class ProveedorVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = ProveedorSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Proveedor.objects.all().order_by('nombre')
        else:
            return Proveedor.objects.filter(instancia=perfil.instancia).order_by('nombre')

""" """
class CompraVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = CompraSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return Compra.objects.all().order_by('empresa', 'Proveedor', 'total')
        else:
            return Compra.objects.filter(instancia=perfil.instancia).order_by('empresa', 'Proveedor', 'total')

""" """
class DetalleCompraVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = DetalleCompraSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return DetalleCompra.objects.all().order_by('compra', 'producto', 'cantidad', 'precio')
        else:
            return DetalleCompra.objects.filter(instancia=perfil.instancia).order_by('compra', 'producto', 'cantidad', 'precio')

""" """
class NotaCompraVS(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    serializer_class = NotaCompraSerializer

    def create(self, request):
        perfil = Perfil.objects.get(usuario=self.request.user)
        datos = request.data
        datos['instancia'] = perfil.instancia.id
        if (perfil.tipo == 'S'):
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        elif (perfil.tipo == 'A'):
            datos = request.data
            datos['instancia'] = perfil.instancia.id
            serializer = self.get_serializer(data=datos)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            partial = True  # Here I change partial to True
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if (str(request.data['instancia']) == str(perfil.instancia.id)):
                partial = True  # Here I change partial to True
                instance = self.get_object()
                serializer = self.get_serializer(
                    instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        perfil = Perfil.objects.get(usuario=self.request.user)
        instance = self.get_object()
        if (perfil.tipo == 'S'):
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            if (str(instance.instancia.id) == str(perfil.instancia.id)):
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)

    def get_queryset(self):
        perfil = Perfil.objects.get(usuario=self.request.user)
        if (perfil.tipo == 'S'):
            return NotaCompra.objects.all().order_by('compra')
        else:
            return NotaCompra.objects.filter(instancia=perfil.instancia).order_by('compra')

# Funciones


def CrearAdmin(data):
    try:
        instan = data['instancia']
        nombreInstancia = instan['nombre'] + " ("+data['username']+")"
        user = User(username=data['username'],
                    email=data['email'], password=data['password'])
        user.save()
        instancia = Instancia(
            nombre=nombreInstancia, activo=instan['activo'], multiempresa=instan['multiempresa'], vencimiento=instan['vencimiento'])
        instancia.save()
        perfil = Perfil(usuario=user, instancia=instancia, tipo='A')
        perfil.save()
        for p in data['permisos']:
            menuInstancia = MenuInstancia(instancia=instancia, menu=p['menu'])
            menuInstancia.save()
            permiso = Permiso(instancia=instancia, perfil=perfil, menuinstancia=menuInstancia,
                              leer=p['leer'], escribir=p['escribir'], borrar=p['borrar'], actualizar=p['actualizar'])
            permiso.save()
        return JsonResponse({"error": "N/A"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return JsonResponse({'error': _(e.args[0])}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([AllowAny])
def CreateSuperUser(request):
    if (Menu.objects.all().count() == 0):
        for m in modelosMENU['modelos']:
            modulo = Modulo(nombre=m['router'])
            modulo.save()
            menu = Menu(router=m['router'], orden=m['orden'])
            menu.modulos = modulo
            menu.save()
            if (m['parent'] != None):
                menu.parent = Menu.objects.get(id=m['parent'])
                menu.save()
    if (Instancia.objects.all().count() == 0):
        instancia = Instancia.objects.create(nombre="Primera",activo=True,multiempresa=True,vencimiento=None)
        for mod in Modulo.objects.all():
            instancia.modulos.add(mod)
        perfilS = Perfil(instancia=instancia,usuario_id=1,activo=True,avatar=None,tipo="S")
        perfilS.save()
        admin = User.objects.create_user(username='admin',password='admin')
        perfilA = Perfil(instancia=instancia,usuario=admin,activo=True,avatar=None,tipo="A")
        perfilA.save()
        usuario = User.objects.create_user(username='usuario',password='usuario')
        perfilU = Perfil(instancia=instancia,usuario=usuario,activo=True,avatar=None,tipo="U")
        perfilU.save()
        for m in Menu.objects.all().order_by('id'):
            menuinstancia = MenuInstancia(instancia_id=1,menu=m,orden=m.orden)
            menuinstancia.save()
            if (m.parent != None):
                menuinstancia.parent = MenuInstancia.objects.get(menu__id=m.parent.id)
                menuinstancia.save()
        # for p in MenuInstancia.objects.filter(instancia=instancia):
        #     permiso = None
        #     permiso = Permiso(instancia=instancia,menuinstancia_id=p.id,perfil_id=2,crear=p['crear'],leer=p['leer'],editar=p['editar'],eliminar=p['eliminar'])
        #     permiso.save()
        return Response("Super creado")
    else:
        return Response("Ya existe un superusuario")
    return Response('Menu.objects.all()')


@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def CrearNuevoUsuario(request):
    data = json.load(request.body)
    try:
        usuario = User.objects.filter(email=data['email'])
        if (usuario):
            return JsonResponse({"error": "Email"}, status=status.HTTP_400_BAD_REQUEST)
        elif (data['tipo'] == 'A' & request.user.perfil.tipo == 'S'):
            return CrearAdmin(data)
        else:
            instan = data['instancia']
            user = User(username=data['username'],email=data['email'],password=data['password'])
            user.save()
            if (request.user.perfil.tipo == 'S'):
                # Instancia igual a la instancia dada por el superusuario (instancia=data['instancia'])
                perfil = Perfil(usuario=user,instancia=data['instancia'],tipo=data['tipo'])
                perfil.save()
                for p in data['permisos']:
                    for mi in MenuInstancia.objects.filter(instancia=data['instancia']):
                        if (mi.id == p['menu']):
                            permiso = None
                            permiso = Permiso(instancia=instan['id'],perfil=perfil,menuinstancia=p['menu'],
                                            leer=p['leer'],escribir=p['escribir'],borrar=p['borrar'],actualizar=p['actualizar'])
                            permiso.save()
                return JsonResponse({"error": "N/A"}, status=status.HTTP_201_CREATED)
            elif (request.user.perfil.tipo == 'A'):
                if (data['tipo'] == "U" or data['tipo'] == "V"):
                    # Instancia igual a la instancia del perfil del usuario que hace la peticion (instancia = request.user.perfil.instancia)     
                    perfil = Perfil(usuario=user,instancia=request.user.perfil.instancia,tipo=data['tipo'])
                    perfil.save()
                    for p in data['permisos']:
                        for mi in MenuInstancia.objects.filter(instancia=data['instancia']):
                            if (mi.id == p['menu']):
                                permiso = None
                                permiso = Permiso(instancia=request.user.perfil.instancia,perfil=perfil,menuinstancia=p['menu'],
                                                leer=p['leer'],escribir=p['escribir'],borrar=p['borrar'],actualizar=p['actualizar'])
                                permiso.save()
                    return JsonResponse({"error": "N/A"}, status=status.HTTP_201_CREATED)
                else:
                    return JsonResponse({"error": "Forbidden, user type not allowed",}, status=status.HTTP_403_FORBIDDEN)
            else:
                return JsonResponse({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return JsonResponse({'error': _(e.args[0])}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def ObtenerMenu(request):
    menus = { 'router': 'root', 'children': []}
    def VerificarHijos (objetoPadre):
        if (MenuInstancia.objects.filter(parent=objetoPadre.id).count() > 0 or Menu.objects.filter(parent=objetoPadre.id).count() > 0):
            return True
        else:
            return False
    if (request.user.perfil.tipo == "S"):
        primeros = Menu.objects.filter(parent=None).order_by('orden')
        for p in primeros:
            if VerificarHijos(p):
                primero = { 'router': '', 'children': []}
                primero['router'] = p.router.replace('-','')
                for s in Menu.objects.filter(parent=p.id).order_by('orden'):
                    if VerificarHijos(s):
                        segundo = { 'router': '', 'children': []}
                        segundo['router'] = s.router
                        for t in Menu.objects.filter(parent=s.id).order_by('orden'):
                            tercero = t.router
                            segundo['children'].append(tercero)
                        primero['children'].append(segundo)
                    else:
                        segundo = s.router
                        primero['children'].append(segundo)
                menus['children'].append(primero)
            else:
                primero = p.router
                menus['children'].append(primero)
        return Response([menus])
    elif (request.user.perfil.tipo == "A" or request.user.perfil.tipo == "U" or request.user.perfil.tipo == "V"):
        instancia = request.user.perfil.instancia
        menu_instancia = MenuInstancia.objects.filter(menu__modulos__in=instancia.modulos.values_list('id'))
        primeros = menu_instancia.filter(parent=None).order_by('orden')
        for primer in primeros:
            if VerificarHijos(primer):
                primero = { 'router': '', 'children': []}
                nombrePrimero = primer.menu.router
                primero['router'] = nombrePrimero.replace('-','')
                for s in MenuInstancia.objects.filter(parent=primer.id).order_by('orden'):
                    if VerificarHijos(s):
                        segundo = { 'router': '', 'children': []}
                        nombreSegundo = s.menu.router
                        segundo['router'] = nombreSegundo
                        for t in MenuInstancia.objects.filter(parent=s.id).order_by('orden'):
                            tercero = t.menu.router
                            segundo['children'].append(tercero)
                        primero['children'].append(segundo)
                    else:
                        segundo = s.menu.router
                        primero['children'].append(segundo)
                menus['children'].append(primero)
            else:
                primero = primer.menu.router
                menus['children'].append(primero)
        return Response([menus])
    else:
        return JsonResponse({'error': 'Forbidden, unknown user'}, status=status.HTTP_403_FORBIDDEN)


@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def ObtenerColumnas(request):
    data = json.loads(request.body)
    columnas = []
    try:
        for f in eval(data['value'])._meta.get_fields():
            JsonCol = {
                'select': False,
                'title': f.name.capitalize(),
                'dataIndex': f.name,
                'align': 'left'
            }
            columnas.append(JsonCol)
        return Response(columnas)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)

# @api_view(["POST"])
# @csrf_exempt
# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
# def crearlista(request):
#     data = json.loads(request.body)
#     try:
#         lista = ListaPrecio(nombre= data['nombre'], activo=data['activo'])
#         lista.save()
#         return Response('exitoso')
#     except ObjectDoesNotExist as e:
#         return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualiza_pedido(request):
    payload = json.loads(request.body)
    try:
        pedido_id = Pedido.objects.get(id=payload['idpedido'])
        detashepedido = DetallePedido.objects.filter(pedido=pedido_id)
        id_dpedidos = []
        total_proforma = 0.0
        for dpedidos in detashepedido:
            id_dpedidos.append(dpedidos.id)
        for i in payload['data']:
            inventario = Inventario.objects.get(id=i['inventario'])
            if i['id'] != None:
                # print(i['cantidada'], inventario.disponible)
                indexpedido = None
                for index, item in enumerate(detashepedido):
                    if item.id == i['id']:
                        indexpedido = index
                cantidadanterior = detashepedido[indexpedido].cantidada
                # print(cantidadanterior)
                nuevodisponible = i['cantidada'] - cantidadanterior
                inventario.disponible -= nuevodisponible
                inventario.bloqueado += nuevodisponible
            perfil = Perfil.objects.get(usuario=request.user)
            lista_precio = ListaPrecio.objects.get(id=i['lista_precio'])
            producto = Producto.objects.get(id=i["producto"])
            instancia = Instancia.objects.get(perfil=perfil.id)
            cantidad = int(i["cantidada"])

            """totalp = cantidad * (producto.costo + (producto.costo * (lista_precio.porcentaje /100)))""" # Dividir totalp en dos partes
            precio_unidad = producto.costo + (producto.costo * (lista_precio.porcentaje /100)) # Calcular el precio de cada producto
            totalp = cantidad * precio_unidad # Calcular el precio final segun la cantidad
            total_proforma += float(totalp)

            pedido = pedido_id
            nuevo_componente = DetallePedido(lote=i["lote"],total_producto=totalp,lista_precio=lista_precio,instancia_id=instancia.id,pedido=pedido,cantidada=cantidad,producto=producto,inventario=inventario)
            nuevo_componente.save()
            if i['id'] == None:
                inventario.disponible = int(inventario.disponible) - cantidad
                inventario.bloqueado = int(inventario.bloqueado) + cantidad
            inventario.save()
            # print(inventario.disponible) # 41 (37)
        pedido_id.total = total_proforma
        pedido_id.save()
        DetallePedido.objects.filter(id__in=id_dpedidos).delete()
        return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': e}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
def ObtenerHistorico(request):
    from django.db.models import CharField, Value
    df = pd.DataFrame()
    try:
        # uid = User.objects.get(username=payload['username'])
        uid = request.user
        # modelo = payload['model']
#        modelo = apps.get_model(app_label='backend', model_name=payload['model'])
        # uid = 1
        betados = ["<class 'backend.models.Modulo'>"]
        if uid is not None:
            for model in apps.get_app_config('backend').get_models():
                if('Historical' not in str(model) and str(model) not in betados):
                    df = pd.DataFrame.append(df,list(model.history.all().values('history_date', 'history_type','history_user_id').annotate(modelo=Value(str(model).replace('backend.models.',''), output_field=CharField())).order_by('-id')))
                    df.reset_index(drop=True, inplace=True)
                    dfx = df.sort_values(by='history_date', ascending=False).head(5)
                    data = []
                    for index, row in dfx.iterrows():
                        tipo = ""
                        if(row["history_type"]=="+"):
                            tipo = 'Creado'
                        elif(row["history_type"]=="-"):
                            tipo = 'Eliminado'
                        else:
                            tipo = 'Editado'
                        data.append({'date':row['history_date'],'type':tipo, 'model':str(row['modelo']).replace("<class '",'').replace("'>",'')})
        return JsonResponse({'mensaje': data}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def validacion_pedido(request):
    payload = json.loads(request.body)
    try:
        # print(payload)
        pedido = Pedido.objects.get(id=payload['idpedido'])
        decision = payload['decision']
        detashepedido = DetallePedido.objects.filter(pedido=pedido)
        perfil = Perfil.objects.get(usuario=request.user)
        instancia = Instancia.objects.get(perfil=perfil.id)
        if payload['decision'] == 'Rechazado':
            pedido.estatus = 'C'
            pedido.save()
            for deta in detashepedido:
                inventario = Inventario.objects.get(id=deta.inventario.id)
                inventario.bloqueado = inventario.bloqueado - deta.cantidada
                inventario.disponible = inventario.disponible + deta.cantidada
                inventario.save()
            return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
        else:
            pedido.estatus = 'A'
            pedido.save()
            ## Se crea una nueva proforma, en base a los datos del pedido
            nueva_proforma = Proforma(pedido=pedido,instancia=instancia)
            nueva_proforma.cliente = pedido.cliente
            nueva_proforma.vendedor = pedido.vendedor
            nueva_proforma.empresa = pedido.empresa
            nueva_proforma.nombre_cliente = pedido.cliente.nombre
            nueva_proforma.identificador_fiscal = pedido.cliente.identificador
            nueva_proforma.direccion_cliente = pedido.cliente.ubicacion
            nueva_proforma.telefono_cliente = pedido.cliente.telefono
            nueva_proforma.save()
            # Se crea el detalle de la proforma con la información asociada en el detalle pedido
            for deta in detashepedido:
                nuevo_detalle = DetalleProforma(
                    proforma=nueva_proforma,
                    lista_precio = deta.lista_precio,
                    inventario=deta.inventario,
                    cantidada=deta.cantidada,
                    lote = deta.lote,
                    producto = deta.producto,
                    precio = deta.producto.costo + (deta.producto.costo * (deta.lista_precio.porcentaje / 100)),
                    total_producto = deta.total_producto,
                    instancia=instancia
                )
                nuevo_detalle.save()
                nueva_proforma.total += deta.total_producto
                nueva_proforma.save()
                inventario = Inventario.objects.get(id=deta.inventario.id)
                inventario.bloqueado = inventario.bloqueado - deta.cantidada
                inventario.save()
            return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': e}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

""" """
from django_renderpdf.views import PDFView
from django.contrib.auth.mixins import LoginRequiredMixin
class PDFPedido(PDFView):
    template_name = 'pedido.html'
    allow_force_html = True
    def get_context_data(self, *args, **kwargs):
        # """Pass some extra context to the template."""
        context = super().get_context_data(*args, **kwargs)
        pedido = Pedido.objects.get(id=kwargs['id_pedido'])
        # total_costo = float(proforma.total)
        value = {'data':[]}
        # total_calculado = 0
        agrupador = DetallePedido.objects.filter(pedido=pedido).values('producto').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada'))
        for dato in agrupador:
            productox = Producto.objects.get(id=dato['producto'])
            valuex = {'datax':[]}
            total_cantidad = 0
            # precio_unidad = 0
            # costo_total = 0
            mostrar = True
            detallado = DetallePedido.objects.filter(pedido=pedido,producto=productox).order_by('producto__id')
            if productox.lote == True and len(detallado) > 1:
                for detalle in detallado:
                    valuex['datax'].append({'lote':detalle.lote,'cantidad':detalle.cantidada})
                    total_cantidad += detalle.cantidada
                    # precio_unidad = detalle.precio
            elif productox.lote == True and len(detallado) == 1:
                valuex['datax'] = ''
                mostrar = False
                for detalle in detallado:
                    valuex['datax'] = detalle.lote
                    total_cantidad += detalle.cantidada
                    # precio_unidad = detalle.precio
            else:
                mostrar = False
                for detalle in detallado:
                    total_cantidad += detalle.cantidada
                    # precio_unidad = detalle.precio
                valuex['datax'] = None
            # costo_total = float(precio_unidad) * float(total_cantidad)
            # total_calculado += round(costo_total, 2)
            value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad})
        context['productos'] = value['data']
        # if (float(total_calculado) == float(total_costo)):
        #     context['total'] = total_calculado
        # else:
        #     context['total'] = 'Error'
        context['pedido'] = pedido
        print(value['data'])
        return context

""" """
class PDFProforma(PDFView):
    template_name = 'proforma.html'
    allow_force_html = True
    def get_context_data(self, *args, **kwargs):
        # """Pass some extra context to the template."""
        context = super().get_context_data(*args, **kwargs)
        proforma = Proforma.objects.get(id=kwargs['id_proforma'])
        total_costo = float(proforma.total)
        value = {'data':[]}
        total_calculado = 0
        agrupador = DetalleProforma.objects.filter(proforma=proforma).values('producto','precio').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada'))
        for dato in agrupador:
            productox = Producto.objects.get(id=dato['producto'])
            valuex = {'datax':[]}
            total_cantidad = 0
            precio_unidad = 0
            costo_total = 0
            mostrar = True
            detallado = DetalleProforma.objects.filter(proforma=proforma,producto=productox).order_by('producto__id')
            if productox.lote == True and len(detallado) > 1:
                for detalle in detallado:
                    valuex['datax'].append({'lote':detalle.lote,'cantidad':detalle.cantidada})
                    total_cantidad += detalle.cantidada
                    precio_unidad = detalle.precio
            elif productox.lote == True and len(detallado) == 1:
                valuex['datax'] = ''
                mostrar = False
                for detalle in detallado:
                    valuex['datax'] = detalle.lote
                    total_cantidad += detalle.cantidada
                    precio_unidad = detalle.precio
            else:
                mostrar = False
                for detalle in detallado:
                    total_cantidad += detalle.cantidada
                    precio_unidad = detalle.precio
                valuex['datax'] = None
            costo_total = float(precio_unidad) * float(total_cantidad)
            total_calculado += round(costo_total, 2)
            value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad,'precio':precio_unidad,'total_producto':round(costo_total, 2)})
        context['productos'] = value['data']
        if (float(total_calculado) == float(total_costo)):
            context['total'] = total_calculado
        else:
            context['total'] = 'Error'
        context['proforma'] = proforma
            # with open('/log/proforma%s.pdf'%datetime(), 'wb') as f:
            #     pdf.write(response.content)
        return context

""" """
class PDFFactura(PDFView):
    template_name = 'factura.html'
    allow_force_html = True
    def get_context_data(self, *args, **kwargs):
        conversion = None
        try:
            conversion = TasaConversion.objects.filter(fecha_tasa__date=datetime.datetime.today().date()).latest('fecha_tasa__date')
        except:
            conversion = TasaConversion.objects.latest('fecha_tasa__date')
        # """Pass some extra context to the template."""
        context = super().get_context_data(*args, **kwargs)
        factura = Factura.objects.get(id=kwargs['id_factura'])
        subtotal = float(factura.subtotal)
        total_costo = round(float(factura.total) * conversion.valor,2)
        value = {'data':[]}
        total_calculado = 0
        agrupador = DetalleFactura.objects.filter(factura=factura).values('producto','precio').annotate(total=Sum('total_producto'),cantidad=Sum('cantidada'))
        for dato in agrupador:
            productox = Producto.objects.get(id=dato['producto'])
            valuex = {'datax':[]}
            total_cantidad = 0
            precio_unidad = 0.0
            costo_total = 0.0
            mostrar = True
            detallado = DetalleFactura.objects.filter(factura=factura,producto=productox).order_by('producto__id')
            if productox.lote == True and len(detallado) > 1:
                for detalle in detallado:
                    valuex['datax'].append({'lote':detalle.lote,'cantidad':detalle.cantidada})
                    total_cantidad += float(detalle.cantidada)
                    precio_unidad = float(detalle.precio) * conversion.valor
            elif productox.lote == True and len(detallado) == 1:
                valuex['datax'] = ''
                mostrar = False
                for detalle in detallado:
                    valuex['datax'] = detalle.lote
                    total_cantidad += float(detalle.cantidada)
                    precio_unidad = float(detalle.precio) * conversion.valor
            else:
                mostrar = False
                for detalle in detallado:
                    total_cantidad += float(detalle.cantidada)
                    precio_unidad = float(detalle.precio) * conversion.valor
                valuex['datax'] = None
            costo_total = precio_unidad * total_cantidad
            total_calculado += costo_total
            value['data'].append({'producto_nombre':productox.nombre,'producto_sku':productox.sku,'detalle':valuex['datax'],'mostrar':mostrar,'cantidad':total_cantidad,'precio':precio_unidad,'total_producto':round(costo_total, 2)})
        context['productos'] = value['data']
        subtotal_conversion = subtotal * conversion.valor
        if (float(total_calculado) == float(subtotal_conversion)):
            context['subtotal'] = subtotal_conversion
            context['total'] = total_costo
        else:
            context['subtotal'] = 'Error'
            context['total'] = 'Error'
        context['factura'] = factura
        return context

@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def generar_factura(request):
    payload = json.loads(request.body)
    try:
        # print(payload)
        proforma = Proforma.objects.get(id=payload['idproforma'])
        detasheproforma = DetalleProforma.objects.filter(proforma=proforma)
        perfil = Perfil.objects.get(usuario=request.user)
        instancia = Instancia.objects.get(perfil=perfil.id)
        nueva_factura = Factura(proforma=proforma,instancia=instancia)
        nueva_factura.nombre_empresa = proforma.empresa.nombre
        nueva_factura.direccion_empresa =  proforma.empresa.direccion_fiscal
        nueva_factura.id_cliente = proforma.cliente.id
        nueva_factura.nombre_cliente = proforma.cliente.nombre
        nueva_factura.identificador_fiscal = proforma.cliente.identificador
        nueva_factura.direccion_cliente = proforma.cliente.ubicacion
        nueva_factura.telefono_cliente = proforma.cliente.telefono
        nueva_factura.correo_cliente = proforma.cliente.correo
        nueva_factura.id_vendedor = proforma.cliente.id
        nueva_factura.nombre_vendedor = proforma.vendedor.nombre
        nueva_factura.telefono_vendedor = proforma.vendedor.telefono
        nueva_factura.impuesto = 16
        nueva_factura.save()
        for deta in detasheproforma:
                nuevo_detalle = DetalleFactura(factura=nueva_factura,
                inventario=deta.inventario,
                inventario_fijo = deta.inventario,
                cantidada=deta.cantidada,
                lote = deta.lote,
                fecha_vencimiento = deta.inventario.fecha_vencimiento,
                producto = deta.producto,
                producto_fijo = deta.producto.nombre,
                precio = deta.producto.costo,
                total_producto = deta.total_producto,
                instancia=instancia
                )
                nuevo_detalle.save()
                nueva_factura.subtotal += float( deta.total_producto)
                nueva_factura.total += float( deta.total_producto) + (float( deta.total_producto) * (float(nueva_factura.impuesto) / 100))
                nueva_factura.save()
        return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': e}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def actualiza_proforma(request):
    payload = json.loads(request.body)
    try:
        # print(payload)
        proforma_id = Proforma.objects.get(id=payload['idproforma'])
        # print(proforma_id)
        detasheproforma = DetalleProforma.objects.filter(proforma=proforma_id)
        id_proformas = []
        total_proforma = 0.0
        for dproformas in detasheproforma:
            id_proformas.append(dproformas.id)
        for i in payload['data']:
            inventario = Inventario.objects.get(id=i['inventario'])
            if i['id'] != None:
                # print(i['cantidada'], inventario.disponible)
                indexpedido = None
                for index, item in enumerate(detasheproforma):
                    if item.id == i['id']:
                        indexpedido = index
                cantidadanterior = detasheproforma[indexpedido].cantidada
                # print(cantidadanterior)
                nuevodisponible = i['cantidada'] - cantidadanterior
                inventario.disponible -= nuevodisponible
            perfil = Perfil.objects.get(usuario=request.user)
            lista_precio = ListaPrecio.objects.get(id=i['lista_precio'])
            producto = Producto.objects.get(id=i["producto"])
            instancia = Instancia.objects.get(perfil=perfil.id)
            cantidad = int(i["cantidada"])
            """totalp = cantidad * (producto.costo + (producto.costo * (lista_precio.porcentaje /100)))""" # Dividir totalp en dos partes
            precio_unidad = float(producto.costo) + (float(producto.costo) * (float(lista_precio.porcentaje)/100.0)) # Calcular el precio del producto en la venta
            totalp = cantidad * precio_unidad # Calcular el precio final del detalle segun la cantidad
            total_proforma += float(totalp)

            proforma = proforma_id
            nuevo_componente = DetalleProforma(proforma=proforma,lote=i["lote"],total_producto=totalp,lista_precio=lista_precio,precio=precio_unidad,instancia_id=instancia.id,cantidada=cantidad,producto=producto,inventario=inventario)
            nuevo_componente.save()
            if i['id'] == None:
                inventario.disponible = int(inventario.disponible) - cantidad
            inventario.save()
            # print(inventario.disponible) # 41 (37)
        proforma_id.total = total_proforma
        proforma_id.save()
        # print(id_proformas)
        DetalleProforma.objects.filter(id__in=id_proformas).delete()
        return JsonResponse({'exitoso': 'exitoso'}, safe=False, status=status.HTTP_200_OK)
    except ObjectDoesNotExist as e:
        return JsonResponse({'error': str(e)}, safe=False, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return JsonResponse({'error': e}, safe=False,
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def XLSVista(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="productos.xls"'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Styling Data')
    i = 0
    for m in Marca.objects.all().values():
        estilo = xlwt.easyxf('font: bold 1')
        ws.write(i, 0, 'Marca:',estilo)
        ws.write(i, 1, m['nombre'])
        i = i+1
        ws.write(i, 0, 'Codigo')
        ws.write(i, 1, 'Producto')
        ws.write(i, 2, 'Costo A')
        ws.write(i, 3, 'Costo B')
        ws.write(i, 4, 'Costo c')
        i = i+1
        for p in Producto.objects.filter(marca=m['id']).values():
            ws.write(i, 0, p['sku'])
            ws.write(i, 1, p['nombre'])
            ws.write(i, 2, p['costo'])
            ws.write(i, 3, p['costo_2'])
            ws.write(i, 4, p['costo_3'])
            i = i+1
    wb.save(response)
    return response

# @api_view(["POST, GET"])
# @csrf_exempt
# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
def Value(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="lista.xls"'
    marcas = Marca.objects.all()
    writer = csv.writer(response)  
    for m in marcas:
        writer.writerow(['Marca:' , m.nombre])
        titulos = ['Codigo', 'Producto', 'Costo']
        listas = ListaPrecio.objects.filter(activo=True).order_by('id')
        for lista in listas:
            titulos.append(lista.nombre) 
        writer.writerow(titulos)
        productos = Producto.objects.filter(activo=True,venta=True, marca=m)
        for p in productos:
            texto = [p.sku, p.nombre, p.costo]
            precios = DetalleListaPrecio.objects.filter(producto= p).order_by('listaprecio__id')
            for precio in precios:
                texto.append(precio.precio)
            writer.writerow(texto)
    return response

@api_view(["GET"])
@csrf_exempt
# @authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def PDFGuardar(request):
    try:
        data = request.data
        if not data:
            data['id'] = 1
        host = str(request.get_host())
        principal_url = 'http://%s'%(host)
        url = principal_url+'/apis/v1/pdf-proforma/%s'%(data['id'])
        response = requests.get(url)
        with open('proformas/proforma-%s.pdf'%data['id'], 'wb') as f:
            f.write(response.content)
        return Response(True)
    except:
        return Response(False)