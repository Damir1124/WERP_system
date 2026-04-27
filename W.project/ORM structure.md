zwНиже приведён пример структуры проекта Osnova с распределением таблиц по модулям (Django-приложениям). При этом функционал, помеченный как Osnova Plus, здесь не учитывается.

---

## Структура проекта (Django-проект)

```bash
WERP_project/
├── manage.py
├── WERP_project/  # Корневые настройки (settings, urls, wsgi, asgi)
└── apps/
    ├── clients/   # Модуль учета клиентов
    ├── products/  # Модуль учета позиций (ассортимент, продукты)
    ├── workers/   # Модуль учета сотрудников (работники, курьеры, прочие)
    ├── warehouse/ # Модуль склада (баланс, движение товаров, гараж)
    ├── logistics/ # Модуль логистики (учет доставки, движения позиций)
    └── accounting/# Модуль бухгалтерии
```
---

## Распределение таблиц по приложениям

### 1. **Модуль Clients**

**Таблица: Client**

- **Поля:**
    - `name` – ФИО или название организации
    - `phone` – номер телефона
    - `address` – адрес
    - `balance` – текущий баланс (например, задолженность или предоплата)
    - `note` – примечание
    - `created_at` - время регистрации
    - `updated_at` - время обновления

---

### 2. **Модуль Products

**Таблица: Product**

- **Поля:**
    - `name` – наименование продукта
    - `product_type` – тип продукта (например, аксессуар, кулер, вода, тара)
    - `price` – стоимость
    - `created_at` - время регистрации
    - `updated_at` - время обновления

---

### 3. **Модуль Workers**

**Таблица: Worker**

- **Поля:**
    - `full_name` – ФИО
    - `worker_type` – тип сотрудника (упаковщик, курьер, прочие)
    - `date_for_payed` – дата начала работы или начисления зарплаты
    - `note` – примечание
    - `created_at` - время регистрации
    - `updated_at` - время обновления

---

### 4. **Модуль Warehouse**

**Таблица: StockBalance**

- **Поля:**
    - `product` – FK на таблицу Product
    - `quantity` – текущий остаток на складе
    - `last_received_date` – дата последнего прихода
    - `last_dispatch_date` – дата последнего ухода

**Таблица: StockMovement**

- **Поля:**
    - `sold_product` – FK на Product
    - `contract` – (опционально) FK на контракт (если движение связано с поставкой или продажей)
    - `operation_type` – тип операции (приход, уход)
    - `quantity` – количество
    - `date` – дата операции
    - `note` – примечание

**Таблица: Garage**

- **Поля:**

    - `vehicle_name` – наименование машины
    - `plate_number` – номерной знак
    - `courier` – FK на Worker (если привязан к курьеру)
    - `mileage` – пробег
    - `year` – год выпуска

---

### 5. **Модуль Logistics**

Для базового учета доставок (без расширенного функционала Osnova Plus) можно использовать одну таблицу, которая фиксирует операции доставки.

**Таблица: DeliveryLog**

- **Поля:**
    - `courier` – FK на Couruier
    - `total_quantity` – количество (например, проданных бутылей или возвращенной тары)
    - `date` – дата день
---
**Таблица: DeliveryLogMove**

- **Поля:**
    - `delivery_log` - FK на DeliveryLog
	- `action` – тип операции (например, "взял", "привез", "возврат")
    - `quantity` – количество (например, проданных бутылей или возвращенной тары)
    - `date` – дата день
---
**Таблица: DeliveryJournal**
- **Поля**
    - `courier` – FK на Worker(тип courier)
    - `date` - дата отчета 
    - `total_price` - сумма стоимости(может сделать чтобы сама по стоимости продукта считалась)
    - `pyment_type` - тип оплаты (карта нал бонус(как расходник тоже считатеся))
---
**Таблица: DeliveryJournalProducts**
- **Поля**
    - `note` – адрес или примечание или ориентир
    - `delivery_journal` - FK на DeliveryJournal 
    - `product` - FK на Product
    - `quantity` - количество товара
### 6. **Модуль Accounting (Бухгалтерия)**

**Таблица: Contract**
- **Поля:**
    - `description` – описание контракта
    - `client` - FK на Client
    - `date` – дата заключения
    - `document` – прикрепленные документы (файл или URL)
    - `contract_type` – тип (плюс/минус)
    - `amount` – сумма
    - `note` – примечание

**Таблица: Installment**  
(Учет рассрочки клиентов)

- **Поля:**
    - `id` – уникальный идентификатор
    - `client` – FK на Client
    - `product` – FK на Product (товар, переданный в рассрочку)
    - `total_amount` – общая сумма рассрочки
    - `paid_payment` – сумма которая уже уплочена
    - `due_date` – дата ближайшего платежа
    - `status` – статус рассрочки (`active`, `overdue`, `closed`)
    - `created_at`
    - `updated_at`

**Таблица: PaymentsInstallment 
(Учет взносов рассрочки клиентов)

- **Поля:**
    - `fk(Installment)` – ссылка на рассрочки
    - `date` – дата платежа
    - `amount` – сумма взноса
    - `created_at`

**Таблица: Salary 
(Учет зарплаты и выплат сотрудникам)

- **Поля:**

    - `worker` – FK на Worker
    - `last_payment` – дата последней выплаты
    - `balance` – баланс

**Таблица: SalaryPayment 
(Учет доходов, расходов, прибыли)

- **Поля:**
	- `salary` - FK на Salary
	- `note` - примечание
	- `amount` - сумма 
	- `payment_type` - тип платежа
    - `date` – дата операции

---

## Итоговая схема распределения таблиц

|Модуль|Основные таблицы|
|---|---|
|**Clients**|Client|
|**Positions**|Product|
|**Workers**|Worker|
|**Warehouse**|StockBalance, StockMovement, Garage|
|**Logistics**|DeliveryLog (или, при необходимости, CourierTrip)|
|**Accounting**|Contract, Installment, SalaryPayment, FinancialTransaction|

## Связи
- [[W.project]]
