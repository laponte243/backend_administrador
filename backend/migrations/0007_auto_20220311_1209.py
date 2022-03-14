# Generated by Django 3.2.7 on 2022-03-11 16:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0006_auto_20220309_1138'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detallecompra',
            name='descripcion',
            field=models.TextField(help_text='En caso de no tener producto asociado a la compra se puede colocar una descripcion del rubro', max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='detallefactura',
            name='factura',
            field=models.ForeignKey(help_text='Factura asociada', on_delete=django.db.models.deletion.DO_NOTHING, to='backend.factura'),
        ),
        migrations.AlterField(
            model_name='detallefactura',
            name='inventario_fijo',
            field=models.TextField(help_text='Inventario asociado fijado', max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='detallefactura',
            name='lote',
            field=models.TextField(help_text='Lote del producto fijado', max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='detallefactura',
            name='precio',
            field=models.TextField(default=0, help_text='Precio del producto o servicio a vender fijado', max_length=150),
        ),
        migrations.AlterField(
            model_name='detallefactura',
            name='producto',
            field=models.ForeignKey(help_text='Producto asociada', on_delete=django.db.models.deletion.DO_NOTHING, to='backend.producto'),
        ),
        migrations.AlterField(
            model_name='detallefactura',
            name='producto_fijo',
            field=models.TextField(help_text='Producto asociado fijado', max_length=150),
        ),
        migrations.AlterField(
            model_name='detallefactura',
            name='total_producto',
            field=models.TextField(default=0, help_text='Total final del detalle', max_length=150),
        ),
        migrations.AlterField(
            model_name='historicaldetallecompra',
            name='descripcion',
            field=models.TextField(help_text='En caso de no tener producto asociado a la compra se puede colocar una descripcion del rubro', max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='factura',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='Factura asociada', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='backend.factura'),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='inventario_fijo',
            field=models.TextField(help_text='Inventario asociado fijado', max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='lote',
            field=models.TextField(help_text='Lote del producto fijado', max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='precio',
            field=models.TextField(default=0, help_text='Precio del producto o servicio a vender fijado', max_length=150),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='producto',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='Producto asociada', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='backend.producto'),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='producto_fijo',
            field=models.TextField(help_text='Producto asociado fijado', max_length=150),
        ),
        migrations.AlterField(
            model_name='historicaldetallefactura',
            name='total_producto',
            field=models.TextField(default=0, help_text='Total final del detalle', max_length=150),
        ),
    ]