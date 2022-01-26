# inicio = {'modelos':[
#     {"router": "-Inicio",               "parent":None,"orden":0},
#     {"router": "Dashboard",             "parent":0,"orden":1},]}
# menu = {'modelos': []}
# parent = 0
# for i in inicio['modelos']:
#     counter = 1
#     if i['parent'] == None:
#         parent = counter
#     else:
#         i['parent'] = parent
#     menu['modelos'].append(i)
#     counter += 1
# print(menu)
modelosMENU = {'modelos':[
    # Parents
    {"router": "-Inicio",               "parent":None,"orden":0}, # Principal id:1
    {"router": "Dashboard",             "parent":1,"orden":1}, # -dashboard id:2

    {"router": "-Inventarios",           "parent":None,"orden":1}, # Principal id:3
    {"router": "Almacenes",             "parent":3,"orden":1}, # -Inventarios id:4
    {"router": "Productos",             "parent":3,"orden":2}, # -Inventarios id:5
    {"router": "Inventario",            "parent":3,"orden":3}, # -Inventarios id:6
    # {"router": "Marca",                 "parent":6,"orden":1},
    # {"router": "Unidad",                "parent":6,"orden":1},
    # {"router": "Producto",              "parent":6,"orden":2},
    # {"router": "Almacen",               "parent":6,"orden":3},
    # {"router": "ProductoImagen",        "parent":6,"orden":4},

    {"router": "-Venta",                "parent":None,"orden":2}, # Principal id:7
    {"router": "Cliente",               "parent":7,"orden":1}, # -Ventas id:8
    {"router": "Vendedor",              "parent":7,"orden":2}, # -Ventas id:9
    {"router": "Facturacion",           "parent":7,"orden":5}, # -Ventas id:10
    {"router": "ListaPrecio",           "parent":7,"orden":6}, # -Ventas id:11
    {"router": "Pedido",                "parent":10,"orden":3}, # -Ventas id:12
    {"router": "Proforma",              "parent":10,"orden":4}, # -Ventas id:13
    {"router": "Factura",               "parent":10,"orden":4}, # -Ventas id:14
    # {"router": "ContactoCliente",       "parent":8,"orden":1},
    # {"router": "DetallePedido",         "parent":12,"orden":1},
    # {"router": "DetalleProforma",       "parent":13,"orden":1},
    # {"router": "DetalleListaPrecio",    "parent":11,"orden":1},
    # {"router": "DetalleFactura",        "parent":14,"orden":1},
    # {"router": "ImpuestosFactura",      "parent":14,"orden":2},
    # {"router": "NumerologiaFactura",    "parent":14,"orden":3},
    # {"router": "NotaFactura",           "parent":14,"orden":4},

    {"router": "-Compra",               "parent":None,"orden":3}, # Principal id:15
    {"router": "Proveedor",             "parent":15,"orden":1}, # -Compras id:16
    {"router": "Compra",                "parent":15,"orden":2}, # -Compras id:17
    # {"router": "DetalleCompra",         "parent":17,"orden":1},
    # {"router": "NotaCompra",            "parent":17,"orden":2},


    {"router": "-Configuracion",        "parent":None,"orden":4}, # Principal id:18
    {"router": "Usuarios_y_permisos",   "parent":18,"orden":1}, # -Configuracion id:19
    {"router": "Empresa",               "parent":18,"orden":2}, # -Configuracion id:20
    {"router": "Avanzado",              "parent":18,"orden":3}, # -Configuracion id:21
    {"router": "ConfiguracionPapeleria","parent":21,"orden":1}, # Avanzado id:22
    {"router": "Impuesto",              "parent":21,"orden":2}, # Avanzado id:23
    {"router": "TasaConversion",        "parent":21,"orden":3}, # Avanzado id:24
    # {"router": "User",                  "parent":19,"orden":1},
    # {"router": "Perfil",                "parent":19,"orden":2},
    # {"router": "Permiso",               "parent":19,"orden":3},
    # {"router": "ContactoEmpresa",       "parent":20,"orden":2},
    # {"router": "Menu",                  "parent":None,"orden":2},
    # {"router": "MenuInstancia",         "parent":None,"orden":1},
]}

# bases = { "modelos": [
#     {"router": "-Utilidades","parent":None,"orden":1}, # Principal
#     {"router": "-Instancia","parent":None,"orden":2}, # Principal
#     {"router": "-Empresas","parent":None,"orden":3}, # Principal
#     {"router": "-Inventarios","parent":None,"orden":4}, # Principal
#     {"router": "-Ventas","parent":None,"orden":5}, # Principal
#     {"router": "-Compras","parent":None,"orden":6}, # Principal
# ]}

# compra = { "modelos": [
#     # Compras
#     {"router": "Proveedor","parent":"-Compras","orden":1}, # -Compras
#     {"router": "Compra","parent":"-Compras","orden":2}, # -Compras
#     # Detalles en Compras
#     {"router": "DetalleCompra","parent":"Compra","orden":1}, # -Compras
#     {"router": "NotaCompra","parent":"Compra","orden":2}, # Compra
# ]}

# for base in bases:
#     modelo = {"router":base["router"], "parent":base["parent"], "orden":base['orden']}
