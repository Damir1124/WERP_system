from django.apps import AppConfig


class BotBridgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bot_bridge'
    verbose_name = 'Мост для Telegram-бота'