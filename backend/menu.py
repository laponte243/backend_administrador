modelosMENU = {'modelos':[
    {
        "router":"-Inicio",
        "parent":None,
        "orden":0
    },
    {
        "router": "Dashboard",
        "parent":"-Inicio",
        "orden":1
    },
    {
        "router": "Tempro",
        "parent":"-Inicio",
        "orden":2
    },
    {
        "router": "-Inventarios",
        "parent":None,
        "orden":1
    },
    {
        "router": "Almacenes",
        "parent":"-Inventarios",
        "orden":1
    },
    {
        "router": "Productos",
        "parent":"-Inventarios",
        "orden":2
    },
    {
        "router": "Inventario",
        "parent":"-Inventarios",
        "orden":3
    },
    # # {
    #     "router": "Marca",
    #     "parent":6,
    #     "orden":1
    # },
    # # {
    #     "router": "Unidad",
    #     "parent":6,
    #     "orden":2
    # }, # Eliminado
    # # {
    #     "router": "Producto",
    #     "parent":6,
    #     "orden":3
    # },
    # # {
    #     "router": "MovimientoInventario",
    #     "parent":6,
    #     "orden":4
    # },
    # # {
    #     "router": "Almacen",
    #     "parent":6,
    #     "orden":5
    # },
    # # {
    #     "router": "ProductoImagen",
    #     "parent":6,
    #     "orden":6
    # },

    {
        "router": "-Venta",
        "parent":None,
        "orden":2
    },
    {
        "router": "Cliente",
        "parent":"-Venta",
        "orden":1
    },
    {
        "router": "Vendedor",
        "parent":"-Venta",
        "orden":2
    },
    {
        "router": "Facturacion",
        "parent":"-Venta",
        "orden":5
    },
    {
        "router": "Pedido",
        "parent":"Facturacion",
        "orden":3
    },
    {
        "router": "Proforma",
        "parent":"Facturacion",
        "orden":4
    },
    {
        "router": "Factura",
        "parent":"Facturacion",
        "orden":4
    },
    {
        "router": "Cobranza",
        "parent":"-Venta",
        "orden":4
    },
    {
        "router": "Notasdepago",
        "parent":"Cobranza",
        "orden":2
    },
    {
        "router": "Comisiones",
        "parent":"Cobranza",
        "orden":3
    },
    # # {
    #     "router": "ListaPrecio",
    #     "parent":7,
    #     "orden":6
    # }, # Eliminado
    # # {
    #     "router": "ContactoCliente",
    #     "parent":8,
    #     "orden":1
    # },
    # # {
    #     "router": "DetallePedido",
    #     "parent":12,
    #     "orden":1
    # },
    # # {
    #     "router": "DetalleProforma",
    #     "parent":13,
    #     "orden":1
    # },
    # # {
    #     "router": "DetalleListaPrecio",
    #     "parent":11,
    #     "orden":1
    # },
    # # {
    #     "router": "DetalleFactura",
    #     "parent":14,
    #     "orden":1
    # },
    # # {
    #     "router": "ImpuestosFactura",
    #     "parent":14,
    #     "orden":2
    # },
    # # {
    #     "router": "NumerologiaFactura",
    #     "parent":14,
    #     "orden":3
    # },
    # # {
    #     "router": "NotaFactura",
    #     "parent":14,
    #     "orden":4
    # },
    {
        "router": "-Compra",
        "parent":None,
        "orden":3
    },
    {
        "router": "Proveedor",
        "parent":"-Compra",
        "orden":1
    },
    {
        "router": "Compra",
        "parent":"-Compra",
        "orden":2
    },
    {
        "router": "-Configuracion",
        "parent":None,
        "orden":4
    },
    {
        "router": "Usuarios_y_permisos",
        "parent":"-Configuracion",
        "orden":1
    },
    {
        "router": "Empresa",
        "parent":"-Configuracion",
        "orden":2
    },
    {
        "router": "Avanzado",
        "parent":"-Configuracion",
        "orden":3
    },
    {
        "router": "ConfiguracionPapeleria",
        "parent":"Avanzado",
        "orden":1
    },
    {
        "router": "Impuesto",
        "parent":"Avanzado",
        "orden":2
    },
    {
        "router": "TasaConversion",
        "parent":"Avanzado",
        "orden":3
    },
    # # {
    #     "router": "User",
    #     "parent":19,
    #     "orden":1
    # },
    # # {
    #     "router": "Perfil",
    #     "parent":19,
    #     "orden":2
    # },
    # # {
    #     "router": "Permiso",
    #     "parent":19,
    #     "orden":3
    # },
    # # {
    #     "router": "ContactoEmpresa",
    #     "parent":20,
    #     "orden":2
    # },
    # # {
    #     "router": "Menu",
    #     "parent":None,
    #     "orden":2
    # },
    # # {
    #     "router": "MenuInstancia",
    #     "parent":None,
    #     "orden":1
    # },
]}