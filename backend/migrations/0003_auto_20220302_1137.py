# Generated by Django 3.2.7 on 2022-03-02 15:37

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0002_auto_20220302_1032'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historicalproforma',
            name='impuesto',
        ),
        migrations.RemoveField(
            model_name='historicalproforma',
            name='nota_entrega',
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='impuesto',
        ),
        migrations.RemoveField(
            model_name='proforma',
            name='nota_entrega',
        ),
        migrations.AddField(
            model_name='factura',
            name='impreso',
            field=models.BooleanField(default=False, help_text='Esta impreso?'),
        ),
        migrations.AddField(
            model_name='historicalfactura',
            name='impreso',
            field=models.BooleanField(default=False, help_text='Esta impreso?'),
        ),
        migrations.AddField(
            model_name='historicalpedido',
            name='estatus',
            field=models.CharField(choices=[('R', 'Revision'), ('A', 'Aprobada'), ('C', 'Cancelada')], default='R', max_length=1),
        ),
        migrations.AddField(
            model_name='historicalproforma',
            name='fecha_proforma',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False, help_text='fecha de generacion del pedido'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalproforma',
            name='impreso',
            field=models.BooleanField(default=False, help_text='Esta impreso?'),
        ),
        migrations.AddField(
            model_name='pedido',
            name='estatus',
            field=models.CharField(choices=[('R', 'Revision'), ('A', 'Aprobada'), ('C', 'Cancelada')], default='R', max_length=1),
        ),
        migrations.AddField(
            model_name='proforma',
            name='fecha_proforma',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, help_text='fecha de generacion del pedido'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='proforma',
            name='impreso',
            field=models.BooleanField(default=False, help_text='Esta impreso?'),
        ),
    ]