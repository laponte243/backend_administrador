from django.apps import AppConfig


class TemproConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tempro'

    # def ready(self):
    #     from . import mqtt
    #     mqtt.client.loop_start()