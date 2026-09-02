"""
Заглушка для будущего экспорта данных в CSV/Excel.
Пока выводит сообщение, что экспорт будет реализован позже.
"""

from django.contrib import admin


class ExportPlaceholderMixin:
    """Mixin: добавляет заглушку экспорта в changelist action."""

    @admin.action(description='📥 Экспорт выбранных (будет позже)')
    def export_placeholder(self, request, queryset):
        self.message_user(
            request,
            '🚧 Экспорт в CSV/Excel будет доступен в следующей версии. '
            'Пока можно использовать копирование из таблицы.',
        )