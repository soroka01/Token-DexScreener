import time
import asyncio
import requests
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.router import Router
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.markdown import bold, italic, text, code

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Бот и диспетчер
BOT_TOKEN = "token"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

USER_CONFIG = {
    455555355: {"base_price": 0.000102, "initial_balance": 58.69},
    466666666: {"base_price": 0.00007, "initial_balance": 74},
}

USER_MESSAGES = {}

# Глобальная переменная для кэширования данных
CACHE = {"data": None, "timestamp": 0}

# Функция для получения цены
def fetch_price():
    global CACHE
    url = "https://api.dexscreener.com/latest/dex/pairs/bsc/0x597d9816ddb9624824591360180a70be6fd26182"
    headers = {
        "Accept": "*/*"
    }
    
    # Проверяем, истек ли кэш (6 секунд)
    current_time = time.time()
    if CACHE["data"] and (current_time - CACHE["timestamp"] < 6):
        logger.info("Используем кэшированные данные")
        return CACHE["data"]
    
    # Выполняем запрос к API
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"Ошибка API: {response.status_code}")
        raise Exception(f"Ошибка API: {response.status_code}")
    
    data = response.json()
    price_usd = float(data["pair"]["priceUsd"])
    price_change = data["pair"]["priceChange"]
    volume = data["pair"]["volume"]
    market_cap = data["pair"]["marketCap"]
    
    # Извлекаем время последнего обновления из заголовка Expires
    last_update_time = response.headers.get("Expires")
    if last_update_time:
        last_update_time = datetime.strptime(last_update_time, "%a, %d %b %Y %H:%M:%S %Z")
        last_update_time = last_update_time + timedelta(hours=5)  # Преобразуем в UTC+5
        last_update_time -= timedelta(seconds=57)  # Вычитаем 57 секунд
        last_update_time_str = last_update_time.strftime("%d.%m %H:%M:%S")
    else:
        last_update_time_str = "Неизвестно" # Если заголовок отсутствует
    
    # Сохраняем данные в кэш
    CACHE["data"] = (price_usd, price_change, volume, market_cap, last_update_time_str)
    CACHE["timestamp"] = current_time
    
    return price_usd, price_change, volume, market_cap, last_update_time_str

# Баланс, профит, PnL
def calculate_metrics(user_id, price_usd):
    config = USER_CONFIG.get(user_id)
    if not config:
        return None
    
    base_price = config["base_price"]
    initial_balance = config["initial_balance"]
    
    current_balance = price_usd / base_price * initial_balance
    profit_percentage = (price_usd - base_price) / base_price * 100
    pnl = current_balance - initial_balance
    
    return current_balance, profit_percentage, pnl

# Функция для получения текущего времени в формате UTC+5
def get_current_time():
    utc_now = datetime.now(timezone.utc) # Получаем текущее время в UTC
    local_time = utc_now + timedelta(hours=5)  # UTC+5
    return local_time.strftime("%d.%m %H:%M:%S")

# Форматирование рыночной капитализации с запятыми
def format_market_cap(value):
    return f"{value:,.0f}$"

# /start
@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь с ID {user_id} запросил /start")
    if user_id not in USER_CONFIG:
        logger.warning(f"Пользователь с ID {user_id} не найден в конфигурации")
        await message.answer("Ваш ID не поддерживается.")
        return
    
    price_usd, price_change, volume, market_cap, last_update_time_str = fetch_price()
    metrics = calculate_metrics(user_id, price_usd)
    if not metrics:
        logger.error(f"Ошибка в расчетах для пользователя {user_id}")
        await message.answer("Ошибка в расчетах.")
        return
    
    current_balance, profit_percentage, pnl = metrics
    
    # Формируем данные для отправки
    response = text(
        f"Текущая цена: {price_usd:.7f}$",
        f"Текущий баланс: {current_balance:.2f}$",
        f"Процент профита: {profit_percentage:.2f}%",
        f"PnL: {pnl:.2f}$",
        f"24H: {price_change['h24']}%",
        f"Капитализация: {format_market_cap(market_cap)}",
        f"{last_update_time_str}",
        sep="\n"
    )
    
    # Отправляем сообщение и сохраняем его ID
    sent_message = await message.answer(response, parse_mode="Markdown")
    USER_MESSAGES[user_id] = sent_message.message_id
    logger.info(f"Сообщение сохранено для пользователя {user_id}: {sent_message.message_id}")

# Автоматическое обновление
async def auto_update():
    while True:
        for user_id, message_id in USER_MESSAGES.items():
            try:
                # Убедимся, что ключ "last_message" существует в CACHE
                if "last_message" not in CACHE:
                    CACHE["last_message"] = {}
                    
                price_usd, price_change, volume, market_cap, last_update_time_str = fetch_price()
                metrics = calculate_metrics(user_id, price_usd)
                if not metrics:
                    logger.warning(f"Пропущено обновление для пользователя {user_id}: ошибка в расчетах")
                    continue
                
                current_balance, profit_percentage, pnl = metrics
                
                # Формируем новое сообщение
                new_response = text(
                    f"Текущая цена: {price_usd:.7f}$",
                    f"Текущий баланс: {current_balance:.2f}$",
                    f"Процент профита: {profit_percentage:.2f}%",
                    f"PnL: {pnl:.2f}$",
                    f"24H: {price_change['h24']}%",
                    f"Капитализация: {format_market_cap(market_cap)}",
                    sep="\n"  # Исключаем строку "Последнее обновление"
                )
                
                # Удаляем строку "Последнее обновление" перед сравнением
                comparison_response = new_response.strip()
                
                cached_message = CACHE["last_message"].get(user_id, "").strip()
                
                # Проверяем, изменилось ли сообщение
                if cached_message == comparison_response:
                    logger.info(f"Данные для пользователя с ID {user_id} не изменились, обновление пропущено")
                    continue
                
                # Обновляем сообщение
                await bot.edit_message_text(
                    f"{new_response}\n\n{last_update_time_str}",
                    chat_id=user_id,
                    message_id=message_id,
                    parse_mode="Markdown"
                )
                CACHE["last_message"][user_id] = comparison_response  # Сохраняем только данные без времени
                logger.info(f"Сообщение обновлено для пользователя с ID {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении для пользователя {user_id}: {e}")
        await asyncio.sleep(6)  # 6 секунд ожидания перед обновлением

# Запуск бота
async def on_startup(_):
    logger.info("Бот запущен и готов к работе.")

async def main():
    dp.include_router(router)
    asyncio.create_task(auto_update())  # автоматическое обновление
    logger.info("Задача auto_update запущена")
    await bot.delete_webhook(drop_pending_updates=True)
    await on_startup(None)
    await dp.start_polling(bot)

# Запуск
if __name__ == "__main__":
    asyncio.run(main())