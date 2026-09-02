"""
Management command: создание групп пользователей и назначение прав.

Группы:
  - Owner       — полный доступ ко всему
  - Dispatcher  — операционная работа (заказы, смены, клиенты)
  - Cashier     — финансы (контракты, транзакции, зарплаты)
  - Warehouse   — склад (остатки, движения, корректировки)
  - Viewer      — только просмотр (read-only)

Запуск: python manage.py setup_groups
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

# Модели, для которых создаются права
APP_MODELS = {
    'logistics': ['couriershift', 'couriertrip', 'order', 'orderitem'],
    'clients': ['client', 'clientaddress'],
    'products': ['product'],
    'workers': ['worker'],
    'warehouse': ['warehouseproduct', 'warehousestockbalance', 'warehousestockmovement',
                  'warehouseinventoryadjustment', 'productwarehousemapping', 'garage'],
    'accounting': ['contract', 'subjectcontract', 'installment', 'installmentitem',
                   'paymentsinstallment', 'salary', 'salarypayment', 'salaryperiod',
                   'financialtransactions', 'finance'],
}

# Какие права (add/change/delete/view) давать каждой группе
# для каждой модели.
# Формат: {группа: {app_label: {model_name: [разрешённые действия]}}}
GROUP_PERMISSIONS = {
    'Owner': {
        '*': '*',  # все права на все модели
    },
    'Dispatcher': {
        'logistics': {
            '*': ['view', 'change', 'add'],
        },
        'clients': {
            '*': ['view', 'change', 'add'],
        },
        'workers': {
            '*': ['view'],
        },
        'products': {
            '*': ['view'],
        },
    },
    'Cashier': {
        'accounting': {
            '*': ['view', 'change', 'add'],
        },
        'logistics': {
            'order': ['view'],
            'couriershift': ['view'],
            'couriertrip': ['view'],
        },
        'clients': {
            'client': ['view'],
        },
    },
    'Warehouse': {
        'warehouse': {
            '*': ['view', 'change', 'add'],
        },
        'products': {
            '*': ['view', 'change'],
        },
        'logistics': {
            'order': ['view'],
        },
    },
    'Viewer': {
        '*': {
            '*': ['view'],
        },
    },
}


def _get_codenames(model_name, actions):
    """Генерирует список codename для модели и действий."""
    if actions == '*':
        actions = ['view', 'add', 'change', 'delete']
    return [f'{a}_{model_name}' for a in actions]


def _get_permissions_for_models(app_label, models_dict, actions):
    """Получает QuerySet Permission для указанных моделей и действий."""
    perms = []
    for model_name, model_actions in models_dict.items():
        if model_actions == '*':
            model_actions = actions
        codenames = _get_codenames(model_name, model_actions)
        for codename in codenames:
            try:
                perm = Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
                perms.append(perm)
            except Permission.DoesNotExist:
                pass  # модель может не иметь такого права
    return perms


class Command(BaseCommand):
    help = 'Создаёт группы пользователей и назначает права'

    def handle(self, *args, **options):
        self.stdout.write('Настройка групп пользователей...')

        for group_name, group_config in GROUP_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.clear()

            if group_config == '*':
                # Owner: все права на все модели
                all_perms = Permission.objects.all()
                group.permissions.set(all_perms)
                self.stdout.write(f'  OK {group_name}: all permissions ({all_perms.count()} pcs)')
                continue

            perms = []
            for app_label, app_config in group_config.items():
                if app_config == '*':
                    # Все модели приложения с указанными действиями
                    models = APP_MODELS.get(app_label, [])
                    for model_name in models:
                        codenames = _get_codenames(model_name, ['view', 'add', 'change', 'delete'])
                        for codename in codenames:
                            try:
                                perm = Permission.objects.get(
                                    content_type__app_label=app_label,
                                    codename=codename,
                                )
                                perms.append(perm)
                            except Permission.DoesNotExist:
                                pass
                else:
                    for model_name, model_actions in app_config.items():
                        codenames = _get_codenames(model_name, model_actions)
                        for codename in codenames:
                            try:
                                perm = Permission.objects.get(
                                    content_type__app_label=app_label,
                                    codename=codename,
                                )
                                perms.append(perm)
                            except Permission.DoesNotExist:
                                pass

            group.permissions.add(*perms)
            self.stdout.write(f'  OK {group_name}: {len(perms)} permissions')

        self.stdout.write(self.style.SUCCESS('Groups setup complete.'))