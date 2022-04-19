@api_view(["GET"])
@csrf_exempt
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def crear_nuevo_usuario(request):
    data=json.load(request.body)
    try:
        perfil_c=Perfil.objects.get(usuario=request.user)
        usuario=User.objects.filter(email=data['email'])
        if (usuario):
            return Response("Ya hay un usuario con el mismo correo",status=status.HTTP_400_BAD_REQUEST)
        elif data['tipo']=='A' and perfil_c.tipo=='S':
            return crear_admin(data)
        elif perfil_c.tipo=='A' and verificar_permiso(perfil,'Usuarios_y_permisos','escribir'):
            data['instancia']=data['instancia'] if perfil.tipo=='S' and data['instancia'] else perfil.instancia.id
            user=User(username=data['username'],email=data['email'],password=generar_clave())
            user.save()
            if (perfil_c.tipo=='S'):
                # Instancia igual a la instancia dada por el superusuario (instancia=data['instancia'])
                perfil=Perfil(usuario=user,instancia=data['instancia'],tipo=data['tipo'])
                perfil.save()
                permisos=data['permisos']
                guardar_permisos(permisos,perfil.id,perfil)
                if perfil.id:
                    return Response(status=status.HTTP_201_CREATED)
                else:
                    return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif (perfil_c.tipo=='A'):
                if (data['tipo']=="U" or data['tipo']=="V"):
                    # Instancia igual a la instancia del perfil del usuario que hace la peticion (instancia=perfil_c.instancia)     
                    perfil=Perfil(usuario=user,instancia=perfil_c.instancia,tipo=data['tipo'])
                    perfil.save()
                    permisos=data['permisos']
                    guardar_permisos(permisos,perfil.id,perfil)
                    if perfil.id:
                        return Response(status=status.HTTP_201_CREATED)
                    else:
                        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)