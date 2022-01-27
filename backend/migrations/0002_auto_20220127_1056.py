# Generated by Django 3.2.7 on 2022-01-27 14:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalmovimientoinventario',
            name='almacen',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='Almacen asociado', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='backend.almacen'),
        ),
        migrations.AddField(
            model_name='movimientoinventario',
            name='almacen',
            field=models.ForeignKey(default=1, help_text='Almacen asociado', on_delete=django.db.models.deletion.DO_NOTHING, to='backend.almacen'),
            preserve_default=False,
        ),
    ]
