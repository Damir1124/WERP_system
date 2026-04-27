from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from apps.workers.models import Worker


class IsCourier(BasePermission):
    """
    Разрешение для аутентификации курьера через Telegram ID.
    Ожидает заголовок X-Telegram-ID с числовым идентификатором Telegram.
    """
    
    def has_permission(self, request, view):
        tg_id = request.headers.get('X-Telegram-ID')
        
        if not tg_id:
            raise AuthenticationFailed('Заголовок X-Telegram-ID обязателен')
        
        try:
            tg_id = int(tg_id)
        except ValueError:
            raise AuthenticationFailed('X-Telegram-ID должен быть числом')
        
        try:
            # Ищем курьера по tg_id
            # ПРИМЕЧАНИЕ: Поле tg_id ещё не добавлено в модель Worker
            # Временно используем поиск по id или другому полю
            # Для тестирования будем искать Worker с id = tg_id
            courier = Worker.objects.get(id=tg_id)
        except Worker.DoesNotExist:
            raise AuthenticationFailed('Курьер с таким Telegram ID не найден')
        
        # Проверяем, что сотрудник является курьером
        if courier.worker_type != Worker.WorkerType.COURIER:
            raise AuthenticationFailed('Доступ только для курьеров')
        
        # Сохраняем объект курьера в запросе для использования в views
        request.courier = courier
        return True


class IsCourierOrReadOnly(BasePermission):
    """
    Разрешение, которое позволяет курьерам выполнять любые действия,
    а другим пользователям - только чтение.
    """
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Для методов записи проверяем аутентификацию курьера
        tg_id = request.headers.get('X-Telegram-ID')
        if not tg_id:
            return False
        
        try:
            tg_id = int(tg_id)
            courier = Worker.objects.get(id=tg_id)
            return courier.worker_type == Worker.WorkerType.COURIER
        except (ValueError, Worker.DoesNotExist):
            return False