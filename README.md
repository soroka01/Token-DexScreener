# 📈 419INU Price Monitor for Telegram

> Небольшой allowlist-прототип только для личного чата: получает одну пару 419INU/USDT из DexScreener и редактирует персональное Telegram-сообщение с расчётным балансом и PnL.

🌐 **Язык:** [Русский](README.md) · [English](README_EN.md)

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Aiogram](https://img.shields.io/badge/aiogram-3.0.0b7-2CA5E0?logo=telegram&logoColor=white)
![Data](https://img.shields.io/badge/Data-DexScreener-5B5BD6)
![Status](https://img.shields.io/badge/Status-prototype-F59E0B)

## ✨ Обзор

Бот отслеживает фиксированную BSC-пару `$419INU/USDT`, допускает только заранее записанных Telegram user IDs и запоминает последний отправленный message ID каждого запустившего `/start` пользователя.

> ⚠️ Используйте бота только в личном чате. `USER_MESSAGES` хранится по Telegram user ID, и background editor использует этот ID как `chat_id`; сообщение, созданное командой `/start` в группе, позже обновить не получится.

| Область | Текущее поведение |
| --- | --- |
| 🎯 Рынок | Одна фиксированная DexScreener pair |
| 👤 Доступ | Локальный allowlist `USER_CONFIG`; только личный чат |
| 💾 Состояние | Только память процесса |
| 🔄 Polling | Цикл с паузой 6 секунд после обработки пользователей |
| 💰 Результат | Расчётный, а не биржевой баланс и PnL |

## 🚀 Возможности

- Получение USD price, 24h change и market cap из DexScreener.
- Общий cache рыночного ответа с TTL 6 секунд.
- Персональные исходные `base_price` и `initial_balance`.
- Один активный message ID на пользователя в личном чате; повторный `/start` делает новое сообщение текущей целью обновлений.
- Редактирование сообщения только при изменении отображаемых рыночных значений.
- Отказ в доступе для ID, которых нет в `USER_CONFIG`.

## 🧮 Как считается результат

Бот не подключается к кошельку и не знает фактическое количество токенов. Он предполагает, что стоимость позиции меняется строго пропорционально цене:

```text
current_balance = price_usd / base_price × initial_balance
profit_percent  = (price_usd - base_price) / base_price × 100
PnL             = current_balance - initial_balance
```

`base_price` и `initial_balance` берутся из `USER_CONFIG`. Комиссии, slippage, покупки, продажи, переводы и изменение количества токенов не учитываются.

## 🔄 Поток выполнения

```text
/start в личном чате
  └─> проверка user_id в USER_CONFIG
       └─> синхронный DexScreener GET или 6-second cache
            └─> расчёт balance / profit / PnL
                 └─> новое Telegram-сообщение

background auto_update
  └─> последовательный обход USER_MESSAGES
       └─> fetch + calculate
            └─> edit_message_text, только если данные изменились
                 └─> sleep(6)
```

HTTP-запрос выполняется библиотекой `requests` внутри async handler/background task. Поэтому сетевой вызов блокирует event loop на время ответа.

## 🏗️ Структура

```text
Token-DexScreener/
├── main.py              # Config, DexScreener client, handlers and update loop
├── requirements.txt     # aiogram beta and requests
├── README.md            # Русская документация
└── README_EN.md         # English documentation
```

## ⚙️ Установка

Проект использует Python 3, но точная матрица версий не проверяется CI.

```powershell
git clone https://github.com/soroka01/Token-DexScreener.git
cd Token-DexScreener
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

На Linux/macOS активируйте окружение командой `source .venv/bin/activate`.

## 🔐 Текущая конфигурация

В этой версии нет env loader или отдельного config-файла. Перед запуском нужно локально изменить `main.py`:

```python
BOT_TOKEN = "replace-with-telegram-token"

USER_CONFIG = {
    123456789: {
        "base_price": 0.000102,
        "initial_balance": 58.69,
    },
}
```

| Поле | Назначение |
| --- | --- |
| `BOT_TOKEN` | Токен Telegram-бота |
| ключ `USER_CONFIG` | Разрешённый Telegram user ID |
| `base_price` | Базовая цена для расчёта доходности |
| `initial_balance` | Исходная расчётная стоимость позиции в USD |

> ⚠️ `main.py` отслеживается Git. Никогда не коммитьте реальный bot token или личные финансовые параметры. Хранение конфигурации в source — известное ограничение прототипа.

## ▶️ Запуск

```powershell
python main.py
```

После запуска разрешённый пользователь отправляет `/start`. Незнакомый ID получает сообщение об отсутствии поддержки.

## 🔗 Источник данных

Проект обращается к конкретной pair:

```text
https://api.dexscreener.com/latest/dex/pairs/bsc/0x597d9816ddb9624824591360180a70be6fd26182
```

Ответ API дополнительно кэшируется самим ботом. DexScreener или его CDN также могут применять собственное кэширование, поэтому polling раз в 6 секунд не гарантирует новую цену при каждом цикле.

## 🛡️ Безопасность

- Бот читает только публичные рыночные данные и не создаёт транзакции.
- Allowlist ограничивает `/start`, но не заменяет безопасное хранение Telegram token.
- Не публикуйте реальные Telegram IDs, token или портфельные параметры.
- После случайного commit токен нужно отозвать через BotFather; удаления строки из новой версии Git недостаточно.

## ⚠️ Ограничения

- Поддерживается только одна зашитая BSC-пара; выбора сети или актива нет.
- Состояние пользователей, cache и message IDs теряется после перезапуска.
- `requests.get()` синхронный и вызывается без timeout или retry.
- Пользователи обрабатываются последовательно, а не параллельно.
- Групповые чаты не поддерживаются: message ID сохраняется по `user_id`, который background editor затем использует как `chat_id`.
- Повторный `/start` создаёт ещё одно сообщение; после этого обновляется только самое новое.
- Фактический интервал равен времени всей обработки плюс `sleep(6)`.
- Отображаемое время строится из HTTP `Expires`, переводится в фиксированный UTC+5 и дополнительно сдвигается на 57 секунд; это не надёжный timestamp сделки или обновления DexScreener.
- `get_current_time()` и полученный `volume` в текущем интерфейсе не используются.
- Используется старая beta-версия `aiogram==3.0.0b7`.
- Нет persistence, graceful task shutdown и runtime configuration.

## 🧪 Тестирование

Автоматических тестов и CI нет. Перед изменениями нужны как минимум:

- проверка формул на фиксированных входных данных;
- mock DexScreener response и ошибочные HTTP/JSON-сценарии;
- allowlist и unknown-user сценарии;
- проверка cache TTL и пропуска неизменившегося сообщения;
- ручной Telegram smoke test;
- `git diff --check`.

Этот список — рекомендуемый scope, а не существующий автоматический pipeline.

## 📄 Лицензия

В репозитории нет файла `LICENSE`. Публикация исходного кода сама по себе не предоставляет разрешение на использование, изменение или распространение; владелец проекта должен выбрать лицензию отдельно.

---

🧪 Компактный прототип для одной конкретной пары — с явными допущениями вместо обещания полноценного портфельного трекера.
