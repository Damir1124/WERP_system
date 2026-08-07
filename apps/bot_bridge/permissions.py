from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from apps.workers.models import Worker


def _require_tg_header() -> bool:
    """
    Строгая проверка заголовка X-Telegram-ID.
    По умолчанию ОТКЛЮЧЕНА (False): система работает без заголовка,
    используя резервную идентификацию (первый курьер / админ).
    Включить позже: BOT_BRIDGE_REQUIRE_TG_HEADER = True (или env-переменная).
    """
    return getattr(settings, 'BOT_BRIDGE_REQUIRE_TG_HEADER', False)


class IsCourier(BasePermission):
    """
    Аутентификация курьера по Telegram ID (заголовок X-Telegram-ID).
    Заголовок опционален (см. _require_tg_header). Если его нет/он
    некорректен и строгая проверка выключена — используется резервный
    курьер (первый в списке), чтобы request.courier всегда был задан.
    """

    def has_permission(self, request, view):
        require = _require_tg_header()
        tg_id = request.headers.get('X-Telegram-ID')

        if tg_id:
            try:
                courier = Worker.objects.get(tg_id=int(tg_id))
            except (ValueError, Worker.DoesNotExist):
                courier = None
            if courier is not None and courier.worker_type == Worker.WorkerType.COURIER:
                request.courier = courier
                return True
            # Работник есть, но он не курьер — доступ запрещён
            if courier is not None:
                raise AuthenticationFailed(
                    'Доступ к Mini App только для курьеров. '
                    'Ваш тип сотрудника: ' + courier.get_worker_type_display()
                )
            # Заголовок есть, но не соответствует ни одному работнику
            if require:
                raise AuthenticationFailed(
                    'Курьер с таким Telegram ID не найден'
                )
            # иначе — резервная идентификация
        else:
            if require:
                raise AuthenticationFailed('Заголовок X-Telegram-ID обязателен')

        # Резервная идентификация — только для разработки
        request.courier = self._fallback_courier()
        return True

    @staticmethod
    def _fallback_courier():
        courier = Worker.objects.filter(worker_type=Worker.WorkerType.COURIER).first()
        if courier is None:
            raise AuthenticationFailed('Нет зарегистрированных курьеров')
        return courier


class IsAdmin(BasePermission):
    """
    Аутентификация администратора по Telegram ID (заголовок X-Telegram-ID).
    Заголовок опционален (см. _require_tg_header).
    """

    def has_permission(self, request, view):
        require = _require_tg_header()
        tg_id = request.headers.get('X-Telegram-ID')

        if tg_id:
            try:
                worker = Worker.objects.get(tg_id=int(tg_id))
            except (ValueError, Worker.DoesNotExist):
                worker = None
            if worker is not None and worker.is_admin:
                request.admin = worker
                return True
            if require:
                raise AuthenticationFailed(
                    'Сотрудник с таким Telegram ID не найден или не является администратором'
                )
        else:
            if require:
                raise AuthenticationFailed('Заголовок X-Telegram-ID обязателен')

        request.admin = self._fallback_admin()
        return True

    @staticmethod
    def _fallback_admin():
        admin = Worker.objects.filter(is_admin=True).first()
        if admin is None:
            raise AuthenticationFailed('Нет зарегистрированных администраторов')
        return admin


class IsCourierOrReadOnly(BasePermission):
    """
    Курьерам — любые действия, остальным — только чтение.
    Когда строгая проверка заголовка выключена, запись тоже разрешена
    без аутентификации.
    """

    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        if not _require_tg_header():
            return True

        tg_id = request.headers.get('X-Telegram-ID')
        if not tg_id:
            return False

        try:
            tg_id = int(tg_id)
            courier = Worker.objects.get(tg_id=tg_id)
            return courier.worker_type == Worker.WorkerType.COURIER
        except (ValueError, Worker.DoesNotExist):
            return False
