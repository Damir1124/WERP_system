"""
ASGI config for WERP_system project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.accounting.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WERP_system.settings')

# Инициализируем Django ASGI application для HTTP запросов
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # HTTP запросы направляем в стандартное Django приложение
    "http": django_asgi_app,
    
    # WebSocket запросы направляем в Accounting consumers
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.accounting.routing.websocket_urlpatterns
        )
    ),
})
