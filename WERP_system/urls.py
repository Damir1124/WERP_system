"""
URL configuration for WERP_system project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import FileResponse, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.db import connection
from apps.workers.models import Worker
from apps.bot_bridge.utils import verify_telegram_init_data, extract_user_id_from_init_data
import os
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """Health-check для мониторинга (UptimeRobot, Better Stack и т.п.).

    Проверяет подключение к БД и Redis. Возвращает 200, если всё работает,
    иначе 503. Не требует авторизации.
    """
    status = {'status': 'ok', 'checks': {}}

    # Проверка БД
    try:
        connection.ensure_connection()
        status['checks']['database'] = 'ok'
    except Exception as exc:  # noqa: BLE001
        logger.error("Health-check: БД недоступна: %s", exc)
        status['checks']['database'] = f'error: {exc}'
        status['status'] = 'error'

    # Проверка Redis
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', timeout=5)
        if cache.get('health_check') == 'ok':
            status['checks']['redis'] = 'ok'
        else:
            status['checks']['redis'] = 'error: cache read failed'
            status['status'] = 'error'
    except Exception as exc:  # noqa: BLE001
        logger.error("Health-check: Redis недоступен: %s", exc)
        status['checks']['redis'] = f'error: {exc}'
        status['status'] = 'error'

    http_status = 200 if status['status'] == 'ok' else 503
    return JsonResponse(status, status=http_status)

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
        response = FileResponse(open(index_path, 'rb'), content_type='text/html')
        # Запрещаем кэширование index.html, чтобы Telegram WebView всегда
        # подхватывал свежую сборку (имя бандла меняется при rebuild).
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    return view


def mini_app_router(request):
    """
    Legacy-роутер. Определяет роль и редиректит в нужный SPA.
    Основная логика теперь в IdentifyView / resolve_user_role.
    """
    import urllib.parse

    init_data = request.GET.get('tgWebAppData', '')
    tg_id = None

    if init_data:
        init_data = urllib.parse.unquote(init_data)
        if verify_telegram_init_data(init_data):
            tg_id = extract_user_id_from_init_data(init_data)

    if tg_id is None:
        init_data = request.headers.get('X-Telegram-Init-Data', '')
        if init_data:
            if verify_telegram_init_data(init_data):
                tg_id = extract_user_id_from_init_data(init_data)

    if tg_id is None:
        try:
            tg_id = int(request.GET.get('tg_id', ''))
        except (ValueError, TypeError):
            tg_id = None

    if tg_id:
        try:
            worker = Worker.objects.filter(tg_id=tg_id).first()
            if worker:
                if worker.worker_type == Worker.WorkerType.OWNER:
                    return redirect('/miniapp/owner/')
                elif worker.worker_type == Worker.WorkerType.OPERATOR:
                    return redirect('/miniapp/operator/')
                elif worker.worker_type == Worker.WorkerType.COURIER:
                    return redirect('/miniapp/courier/')
        except (ValueError, TypeError):
            pass

    # По умолчанию — Launcher (единая точка входа)
    return redirect('/static/miniapp/launcher/index.html')


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

    # Веб-дашборд (P6)
    path('dashboard/', include('apps.dashboard.urls')),

    # Launcher Mini App — единая точка входа для всех пользователей
    path('miniapp/launcher/', serve_spa('launcher'), name='launcher_miniapp'),
    re_path(r'^miniapp/launcher/.*$', serve_spa('launcher'), name='launcher_miniapp_spa'),

    # Mini App для курьера — SPA (все пути отдают index.html)
    path('miniapp/courier/', serve_spa('courier'), name='courier_miniapp'),
    re_path(r'^miniapp/courier/.*$', serve_spa('courier'), name='courier_miniapp_spa'),

    # Mini App для клиента — SPA
    path('miniapp/client/', serve_spa('client'), name='client_miniapp'),
    re_path(r'^miniapp/client/.*$', serve_spa('client'), name='client_miniapp_spa'),

    # Mini App для Owner — SPA
    path('miniapp/owner/', serve_spa('owner'), name='owner_miniapp'),
    re_path(r'^miniapp/owner/.*$', serve_spa('owner'), name='owner_miniapp_spa'),

    # Mini App для Оператора — SPA
    path('miniapp/operator/', serve_spa('operator'), name='operator_miniapp'),
    re_path(r'^miniapp/operator/.*$', serve_spa('operator'), name='operator_miniapp_spa'),

    # Mini App роутер — определяет роль и редиректит на нужный SPA (legacy)
    path('miniapp/', mini_app_router, name='mini_app_router'),

    # Health-check для мониторинга (без авторизации)
    path('health/', health_check, name='health_check'),

    # Корневой URL — редирект на Launcher
    path('', RedirectView.as_view(url='/static/miniapp/launcher/index.html', permanent=False), name='root'),
]

# Статика и медиа в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
