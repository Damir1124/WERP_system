from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class BotBridgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bot_bridge'
    verbose_name = 'Мост для Telegram-бота'

    def ready(self):
        # Импортируем сигналы, если они будут
        try:
            import apps.bot_bridge.signals
            logger.info("Сигналы bot_bridge успешно импортированы")
        except ImportError as e:
            logger.warning(f"Не удалось импортировать сигналы bot_bridge: {e}")