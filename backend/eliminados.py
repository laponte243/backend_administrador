# Funcion para obtener valores del historico
# def Value(request):
#     response=HttpResponse(content_type='application/ms-excel')
#     response['Content-Disposition']='attachment; filename="lista.xls"'
#     writer=csv.writer(response)  
#     for m in Marca.objects.all():
#         writer.writerow(['Marca:' ,m.nombre])
#         titulos=['Codigo','Producto','Costo']
#         listas=ListaPrecio.objects.filter(activo=True).order_by('id')
#         for l in listas:
#             titulos.append(l.nombre) 
#         writer.writerow(titulos)
#         for p in Producto.objects.filter(activo=True,venta=True,marca=m):
#             texto=[p.sku,p.nombre,p.costo]
#             precios=DetalleListaPrecio.objects.filter(producto= p).order_by('listaprecio__id')
#             for precio in precios:
#                 texto.append(precio.precio)
#             writer.writerow(texto)
#     return response
# Funcion para obtener el historico de la aplicacion según la instancia
# @api_view(["GET"])
# @csrf_exempt
# @authentication_classes([TokenAuthentication])
# def obtener_historico(request):
#     from django.db.models import CharField,Value
#     df=pd.DataFrame()
#     try:
#         # uid=User.objects.get(username=payload['username'])
#         uid=request.user
#         # modelo=payload['model']
#         # modelo=apps.get_model(app_label='backend',model_name=payload['model'])
#         # uid=1
#         betados=["<class 'backend.models.Modulo'>"]
#         if uid is not None:
#             for model in apps.get_app_config('backend').get_models():
#                 if('Historical' not in str(model) and str(model) not in betados):
#                     df=pd.DataFrame.append(df,list(model.history.all().values('history_date','history_type','history_user_id').annotate(modelo=Value(str(model).replace('backend.models.',''),output_field=CharField())).order_by('-id')))
#                     df.reset_index(drop=True,inplace=True)
#                     dfx=df.sort_values(by='history_date',ascending=False).head(5)
#                     data=[]
#                     for index,row in dfx.iterrows():
#                         tipo=""
#                         if(row["history_type"]=="+"):
#                             tipo='Creado'
#                         elif(row["history_type"]=="-"):
#                             tipo='Eliminado'
#                         else:
#                             tipo='Editado'
#                         data.append({'date':row['history_date'],'type':tipo,'model':str(row['modelo']).replace("<class '",'').replace("'>",'')})
#         return Response({'mensaje': data},safe=False,status=status.HTTP_200_OK)
#     except ObjectDoesNotExist as e:
#         return Response({'error': str(e)},safe=False,status=status.HTTP_404_NOT_FOUND)
#     except Exception as e:
#         return Response({'error': str(e)},safe=False,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# Funcion tipo vista para eliminar las notas de pago
# class Comision(models.Model):
#     instancia=models.ForeignKey(Instancia,null=False,on_delete=models.DO_NOTHING,help_text="Instancia asociada")
#     cliente=models.ForeignKey(Cliente,null=False,on_delete=models.DO_NOTHING)
#     mes=models.IntegerField(null=False)
#     año=models.IntegerField(null=False)
#     total=models.FloatField(default=0,null=False)
#     def __str__(self):
#         return 'Comision #%s (%s)'%(self.id,self.total)
# class DetalleComision(models.Model):
#     instancia=models.ForeignKey(Instancia,null=False,on_delete=models.DO_NOTHING)
#     comision=models.ForeignKey(Comision,null=False,on_delete=models.DO_NOTHING)
#     nota_pago=models.ForeignKey(NotasPago,null=False,on_delete=models.DO_NOTHING)
#     proforma=models.ForeignKey(Proforma,null=False,on_delete=models.DO_NOTHING)
#     pago=models.FloatField(default=0,null=False)
#     def __str__(self):
#         return 'Comision #%s, NotaPago #%s '%(self.id,self.nota_pago.id)