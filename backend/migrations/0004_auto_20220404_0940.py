# Generated by Django 3.2.7 on 2022-04-04 13:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0003_auto_20220329_1452'),
    ]

    operations = [
        migrations.AddField(
            model_name='detallenotaspago',
            name='saldo_anterior',
            field=models.FloatField(default=0, help_text='saldo anterior de la proforma'),
        ),
        migrations.AlterField(
            model_name='notaspago',
            name='descripcion',
            field=models.TextField(blank=True, help_text='pequeña descripcion', max_length=150, null=True),
        ),
    ]
