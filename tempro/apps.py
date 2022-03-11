from django.apps import AppConfig


class TemproConfig(AppConfig):
    name = 'tempro'

    def ready(self):
        from . import mqtt
        mqtt.client.loop_start()