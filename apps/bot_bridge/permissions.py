"""
Permissions для API бота.
Основаны на поле Worker.worker_type.

Правила:
- COURIER    → доступ к курьерским API
- OPERATOR   → доступ к Admin API
- OWNER      → доступ к Admin API + Owner Dashboard
- OPERATOR   → доступ к операторским API
- is_admin=True → дополнительный доступ к Admin API (обратная совместимость)
- Client     → НЕ имеет доступа к worker API (403)
- Никто не может назначить себе роль через API

Валидация всегда через initData (X-Telegram-Init-Data).
Fallback на X-Telegram-ID только для разработки.
"""
from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from apps.workers.models import Worker


def _resolve_tg_id(request):
    """
    Извлекает tg_id из запроса.
    Приоритет: initData → X-Telegram-ID.
    Возвращает (tg_id, is_init_data) или (None, False).
    """
    init_data = request.headers.get('X-Telegram-Init-Data')
    if init_data:
        from apps.bot_bridge.utils import verify_telegram_init_data, extract_user_id_from_init_data
        if verify_telegram_init_data(init_data):
            tg_id = extract_user_id_from_init_data(init_data)
            if tg_id:
                return tg_id, True

    tg_id_header = request.headers.get('X-Telegram-ID')
    if tg_id_header:
        try:
            return int(tg_id_header), False
        except ValueError:
            pass

    return None, False


def _get_worker(request):
    """Извлекает Worker из запроса по tg_id. Возвращает Worker или None."""
    tg_id, _ = _resolve_tg_id(request)
    if tg_id is None:
        return None
    try:
        return Worker.objects.get(tg_id=tg_id)
    except Worker.DoesNotExist:
        return None


class IsCourier(BasePermission):
    """
    Доступ только для Worker с worker_type=COURIER.
    Устанавливает request.courier.
    """

    def has_permission(self, request, view):
        worker = _get_worker(request)
        if worker is None:
            raise AuthenticationFailed('Пользователь не найден или не авторизован')

        if worker.worker_type != Worker.WorkerType.COURIER:
            raise PermissionDenied(
                f'Доступ только для курьеров. Ваш тип: {worker.get_worker_type_display()}'
            )

        request.courier = worker
        return True


class IsCourierOrOperator(BasePermission):
    """
    Доступ для COURIER, OPERATOR или OWNER.
    Устанавливает request.courier.
    """

    def has_permission(self, request, view):
        worker = _get_worker(request)
        if worker is None:
            raise AuthenticationFailed('Пользователь не найден или не авторизован')

        if worker.worker_type not in (
            Worker.WorkerType.COURIER,
            Worker.WorkerType.OPERATOR,
            Worker.WorkerType.OWNER,
        ):
            raise PermissionDenied('Доступ только для курьеров и операторов')

        request.courier = worker
        return True


class IsAdmin(BasePermission):
    """
    Доступ для Worker с worker_type=OPERATOR, OWNER или is_admin=True.
    Устанавливает request.admin.
    """

    def has_permission(self, request, view):
        worker = _get_worker(request)
        if worker is None:
            raise AuthenticationFailed('Пользователь не найден или не авторизован')

        is_staff_type = worker.worker_type in (Worker.WorkerType.OPERATOR, Worker.WorkerType.OWNER)
        if not is_staff_type and not worker.is_admin:
            raise PermissionDenied(
                f'Доступ только для диспетчеров и админов. Ваш тип: {worker.get_worker_type_display()}'
            )

        request.admin = worker
        return True


class IsOwner(BasePermission):
    """
    Доступ для Worker с worker_type=OWNER, OPERATOR или is_admin=True.
    (Все admin-роли, которые могут открыть Admin Mini App.)
    Устанавливает request.owner.
    """

    @staticmethod
    def _is_owner(worker):
        return (
            worker.is_admin
            or worker.worker_type == Worker.WorkerType.OWNER
            or worker.worker_type == Worker.WorkerType.OPERATOR
        )

    def has_permission(self, request, view):
        worker = _get_worker(request)
        if worker is None:
            raise AuthenticationFailed('Пользователь не найден или не авторизован')

        if not self._is_owner(worker):
            raise PermissionDenied(
                f'Доступ только для администраторов. Ваш тип: {worker.get_worker_type_display()}'
            )

        request.owner = worker
        return True


class IsOperator(BasePermission):
    """
    Доступ для Worker с worker_type=OPERATOR или OWNER.
    Устанавливает request.operator.
    """

    def has_permission(self, request, view):
        worker = _get_worker(request)
        if worker is None:
            raise AuthenticationFailed('Пользователь не найден или не авторизован')

        if worker.worker_type not in (Worker.WorkerType.OPERATOR, Worker.WorkerType.OWNER):
            raise PermissionDenied('Доступ только для операторов')

        request.operator = worker
        return True


class IsCourierOrReadOnly(BasePermission):
    """
    Любому сотруднику — чтение, COURIER — запись.
    """

    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        worker = _get_worker(request)
        if worker is None:
            return False

        return worker.worker_type == Worker.WorkerType.COURIER
