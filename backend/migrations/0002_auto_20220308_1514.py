# Generated by Django 3.2.7 on 2022-03-08 19:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalmenu',
            name='modulos',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='backend.modulo'),
        ),
        migrations.RemoveField(
            model_name='menu',
            name='modulos',
        ),
        migrations.AddField(
            model_name='menu',
            name='modulos',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='backend.modulo'),
        ),
    ]