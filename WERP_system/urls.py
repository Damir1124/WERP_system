"""
URL configuration for WERP_system project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import FileResponse, Http404
import os

# Кастомизация заголовка Django Admin
admin.site.site_header = "Osnova 2.0 — ERP"
admin.site.site_title = "WERP Admin"
admin.site.index_title = "Панель управления"


def serve_spa(spa_name):
    """Возвращает view, который отдаёт index.html собранного SPA из static/miniapp/<spa_name>/"""
    def view(request, *args, **kwargs):
        index_path = os.path.join(settings.BASE_DIR, 'static', 'miniapp', spa_name, 'index.html')
        if not os.path.exists(index_path):
            raise Http404(f"Mini App '{spa_name}' не найден. Выполните npm run build.")
        return FileResponse(open(index_path, 'rb'), content_type='text/html')
    return view


urlpatterns = [
    path('admin/', admin.site.urls),

    # Redirect /api/bot → /api/bot/ (trailing slash)
    path('api/bot', RedirectView.as_view(url='/api/bot/', permanent=True)),

    # API для Telegram бота
    path('api/bot/', include('apps.bot_bridge.urls')),

    # API модулей
    path('api/accounting/', include('apps.accounting.urls')),
    path('api/logistics/', include('apps.logistics.urls')),
    path('api/warehouse/', include('apps.warehouse.urls')),
    path('api/clients/', include('apps.clients.urls')),
    path('api/workers/', include('apps.workers.urls')),
    path('api/products/', include('apps.products.urls')),

    # DRF аутентификация (опционально)
    path('api-auth/', include('rest_framework.urls')),

    # Веб-дашборд (P6) - временно отключено, так как приложение еще не создано
    # path('', include('apps.dashboard.urls')),

    # Mini App для курьера — SPA (все пути отдают index.html)
    path('miniapp/courier/', serve_spa('courier'), name='courier_miniapp'),
    re_path(r'^miniapp/courier/.*$', serve_spa('courier'), name='courier_miniapp_spa'),

    # Mini App для клиента — SPA
    path('miniapp/client/', serve_spa('client'), name='client_miniapp'),
    re_path(r'^miniapp/client/.*$', serve_spa('client'), name='client_miniapp_spa'),

    # Корневой URL — редирект на курьерский Mini App
    path('', RedirectView.as_view(url='/miniapp/courier/', permanent=False), name='root'),
]

# Статика и медиа в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
