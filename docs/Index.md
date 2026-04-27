# База знаний Osnova 2.0

## Архитектура и Модули
* [[Modules_Accounting|Модуль Финансов (Accounting)]] — логика транзакций.
* [[Modules_BotBridge|Мост Telegram (Bot Bridge)]] — API шлюз.
* [[Modules_Clients|Модуль Клиентов (Clients)]] — CRM.
* [[Modules_Logistics|Модуль Логистики (Logistics)]] — ядро доставок.
* [[Modules_Warehouse|Модуль Склада (Warehouse)]] — остатки и автопарк.
* [[Modules_Products|Модуль Продуктов (Products)]] — каталог товаров.
* [[Modules_Workers|Модуль Сотрудников (Workers)]] — курьеры и упаковщики.

## Разбор багов (Post-mortems)
* [[Bugs_RecursiveSignals|Бесконечный цикл в сигналах post_save]]
* [[Bugs_CardProfitCalc|Ошибка подсчета card_profit]]

## Теоретические справки
* [[Concepts_DjangoSignals|Как работают сигналы в Django]]
* [[Concepts_WebSockets|WebSockets и Django Channels]]
* [[Concepts_TelegramBotAuth|Авторизация Telegram бота через tg_id]]

## Ссылки
* [CLAUDE.md](../CLAUDE.md) — архитектурный справочник проекта.
* [Roadmap](../CLAUDE.md#3-roadmap-что-делать-дальше) — приоритетные задачи.