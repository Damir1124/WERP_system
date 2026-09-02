# Концепция: Кэширование Telegram Mini App (TWA) при пересборке Vite

## Проблема

После пересборки фронтенда (`npx vite build`) новые файлы (`index-<newhash>.js`, `index-<newhash>.css`) появляются в [`static/miniapp/courier/`](static/miniapp/courier/), но Telegram WebView продолжает показывать **старую версию** страницы.

Изменения в исходниках есть, сборка прошла успешно, Django перезапущен — а визуально ничего не изменилось.

## Почему так происходит

### Схема раздачи статики

```
Vite сборка
     ↓
static/miniapp/courier/index.html  ← содержит ссылки на assets/index-<hash>.js
     ↓
Django: serve_spa() читает этот index.html и отдаёт браузеру
     ↓
Браузер/WebView скачивает index.html, видит ссылку на index-<hash>.js
     ↓
                  ┌─── ЕСТЬ в кэше? ───→ использует старый файл
                  │
                  └─── НЕТ в кэше? ───→ скачивает новый
```

**Ключевой момент:** Vite при каждой сборке генерирует **новые имена файлов** с хэшами (`index-BNIPcG-n.js` вместо `index-CH5ga1eq.js`). `index.html` обновляется автоматически. НО:

1. Браузер/WebView **кэширует `index.html`** по его URL (`/miniapp/courier/`)
2. Если `index.html` закэширован — браузер **не запрашивает новую версию**
3. Старый `index.html` ссылается на **старые asset-файлы**, которые всё ещё в кэше
4. Пользователь видит старую версию приложения

### Почему WebView кэширует особенно агрессивно

Telegram WebView (и Mini App) использует встроенный браузерный движок, который:

- Кэширует HTML-страницы по умолчанию (даже без `Cache-Control` заголовков)
- Не отправляет запрос `If-None-Match` / `If-Modified-Since` при повторных открытиях
- Может хранить кэш между сессиями (пока не очищен вручную)

## Решение: Cache-Busting через query-параметр

### Что сделали

Добавили `?v=N` к URL скрипта и стилей в [`static/miniapp/courier/index.html`](static/miniapp/courier/index.html):

```html
<!-- ДО (проблема: браузер кэширует index.html → ссылается на старый JS) -->
<script type="module" crossorigin src="/static/miniapp/courier/assets/index-BNIPcG-n.js"></script>

<!-- ПОСЛЕ (?v=2 заставляет браузер загрузить заново) -->
<script type="module" crossorigin src="/static/miniapp/courier/assets/index-BNIPcG-n.js?v=2"></script>
```

### Почему это работает

Браузер считает два URL **разными ресурсами**, если у них разные query-параметры:

| URL | Кэш-ключ |
|-----|----------|
| `/assets/index-BNIPcG-n.js` | `index-BNIPcG-n.js` |
| `/assets/index-BNIPcG-n.js?v=2` | `index-BNIPcG-n.js?v=2` |

Даже если сам `index.html` закэширован — при следующем обновлении страницы браузер увидит `?v=2` и поймёт, что это **новый ресурс**, который нужно скачать.

### А можно лучше?

Да. Вместо ручного `?v=N` можно:

1. **Автоматический timestamp** — передавать через Django-контекст в шаблон:

```python
# В serve_spa() или через middleware
context = {'version': int(time.time())}
# В index.html: <script src="...js?v={{ version }}">
```

2. **Заголовки Cache-Control** — настроить Django/Nginx отдавать `index.html` без кэша:

```python
# В serve_spa()
response = FileResponse(open(index_path, 'rb'), content_type='text/html')
response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
response['Pragma'] = 'no-cache'
response['Expires'] = '0'
return response
```

## Как не попадаться в будущем

1. **После каждой пересборки** — увеличивай `?v=N` (или встрой автоматическую дату)
2. **При тестировании** — используй инкогнито/приватный режим
3. **Если изменения не видны** — очисти кэш Telegram: *Настройки → Приложения → Telegram → Память → Очистить кэш*
4. **Hard refresh** — `Ctrl+Shift+R` / `Cmd+Shift+R` принудительно сбрасывает кэш страницы

## Связанные файлы

- [`static/miniapp/courier/index.html`](static/miniapp/courier/index.html) — точка входа SPA (реально отдаётся Django)
- [`templates/miniapp/courier/index.html`](templates/miniapp/courier/index.html) — НЕ используется (запасной шаблон)
- [`WERP_system/urls.py:19`](WERP_system/urls.py:19) — `serve_spa()` читает из `static/miniapp/`
- [`frontend/courier/vite.config.js`](frontend/courier/vite.config.js) — `outDir: '../../static/miniapp/courier'`

## Связанные концепции

- [[Concepts_TelegramMiniApp|Telegram Mini App (TWA) — полное руководство]]
