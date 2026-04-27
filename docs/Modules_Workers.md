# Модуль Workers

**Назначение:** Управление сотрудниками и курьерами.

## Модели

### Worker
Сотрудник системы.
- `full_name` - ФИО
- `phone` - телефон
- `tg_id` - Telegram ID для связи с ботом
- `worker_type` (Courier/Operator/Manager) - тип сотрудника
- `date_for_payed` - дата следующей выплаты
- `is_active` - активен ли сотрудник

## Логика
- Аутентификация курьеров через Telegram ID
- Связь с Garage (один курьер - одна машина)
- Расчет зарплат через модуль Accounting

## Связи
- `Garage.courier` → `Worker` (OneToOne)
- `DeliveryJournal.courier` → `Worker` (ForeignKey)
- `Salary.worker` → `Worker` (ForeignKey)

## API для бота
- Получение информации о курьере
- Подтверждение доставки
- Изменение статуса заказа

## Задачи
- Интеграция с Telegram Mini App
- Уведомления о новых заказах
- Геолокация курьеров в реальном времени

[[Index]] | [[Modules_Accounting]] | [[Modules_Logistics]]