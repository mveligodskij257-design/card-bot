import asyncio
import random
import os
import time
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

TOKEN = "8949300577:AAFNwKw0t2Dta5WvUmKXRoqmxS8LN9wzsPg"

bot = Bot(token=TOKEN)
dp = Dispatcher()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

user_cooldowns = {}
user_inventories = {}
COOLDOWN_TIME = 5# 5 секунд в секундах

CARDS = [
    {"id": "card1", "title": "Максим Тайлер Дерден", "rarity": "Легендарный 🟡", "weight": 5, "filename": "card1.jpg"},
    {"id": "card2", "title": "Максим инспектор", "rarity": "Эпический 🟣", "weight": 15, "filename": "card2.jpg"},
    {"id": "card3", "title": "Максим ручка", "rarity": "Обычный ⚪", "weight": 50, "filename": "card3.jpg"},
    {"id": "card4", "title": "Соня жируха", "rarity": "Редкий 🔵", "weight": 30, "filename": "card4.jpg"},
    {"id": "card5", "title": "Ева Яндере", "rarity": "Эпический 🟣", "weight": 15, "filename": "card5.jpg"},
    {"id": "card6", "title": "Соня рыба-сом", "rarity": "Эпический 🟣", "weight": 15, "filename": "card6.jpg"},
    {"id": "card7", "title": "Соня ручка", "rarity": "Обычный ⚪", "weight": 50, "filename": "card7.jpg"},
    {"id": "card8", "title": "Лиза крутая", "rarity": "Редкий 🔵", "weight": 30, "filename": "card8.jpg"},
    {"id": "card9", "title": "Ева Gandonio", "rarity": "Легендарный 🟡", "weight": 5, "filename": "card9.jpg"},
    {"id": "card10", "title": "Ева чикатило", "rarity": "Эпический 🟣", "weight": 15, "filename": "card10.jpg"},
    {"id": "card11", "title": "Ева тюльпан", "rarity": "Обычный ⚪", "weight": 50, "filename": "card11.jpg"},
    {"id": "card12", "title": "Соня гимнастка", "rarity": "Епический 🟣", "weight": 15, "filename": "card12.jpg"},
    {"id": "card13", "title": "Ева пляшко праголино", "rarity": "Редкий 🔵", "weight": 30, "filename": "card13.jpg"},
    {"id": "card14", "title": "Соня тоска", "rarity": "Епический 🟣", "weight": 15, "filename": "card14.jpg"},
    {"id": "card15", "title": "Соня ЖД знак", "rarity": "Эпический 🟣", "weight": 15, "filename": "card15.jpg"},
    {"id": "card16", "title": "Максим разьебало о лемона", "rarity": "Эпический 🟣", "weight": 15, "filename": "card16.jpg"},
    {"id": "card17", "title": "Максим гитлер", "rarity": "Легендарный 🟡", "weight": 5, "filename": "card17.jpg"},
    {"id": "card18", "title": "Соня разьебаная лемоном", "rarity": "Епический 🟣", "weight": 15, "filename": "card18.jpg"},
    {"id": "card19", "title": "Соня яндере", "rarity": "Епический 🟣", "weight": 15, "filename": "card19.jpg"},
    {"id": "card20", "title": "Ева котость", "rarity": "Легендарный 🟡", "weight": 5, "filename": "card20.jpg"}
]

TOTAL_WEIGHT = sum(card["weight"] for card in CARDS)

# --- ВЕБ-СЕРВЕР ДЛЯ СТАБИЛЬНОГО СТАТУСА LIVE НА RENDER ---
async def handle(request):
    return web.Response(text="Card Bot is running 24/7!")

async def start_website():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- МЕНЮ И КНОПКИ ---
def get_main_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="🔎 Искать карточку", callback_data="action_find"),
            InlineKeyboardButton(text="🎒 Инвентарь", callback_data="action_inventory")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command="start", description="Головне меню"),
        BotCommand(command="cdfind", description="Пошук нових карток"),
        BotCommand(command="inventory", description="Ваш інвентар")
    ]
    await bot.set_my_commands(main_menu_commands)

# --- ЛОГИКА ПОИСКА ---
async def perform_find(user_id: int, user_name: str, message: types.Message):
    current_time = time.time()
    
    if user_id in user_cooldowns:
        time_passed = current_time - user_cooldowns[user_id]
        if time_passed < COOLDOWN_TIME:
            remaining_seconds = int(COOLDOWN_TIME - time_passed)
            hours = remaining_seconds // 3600
            minutes = (remaining_seconds % 3600) // 60
            seconds = remaining_seconds % 60
            time_str = f"{hours} ч. {minutes} мин. {seconds} сек." if hours > 0 else f"{minutes} мин. {seconds} сек."
            
            await message.answer(
                f"⏳ <b>{user_name}</b>, искать карточки можно только раз в 2 часа!\n"
                f"Следующая попытка доступна через: <b>{time_str}</b>",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
            return

    user_cooldowns[user_id] = current_time

    weights = [card["weight"] for card in CARDS]
    card = random.choices(CARDS, weights=weights, k=1)[0]
    
    if user_id not in user_inventories:
        user_inventories[user_id] = {}
    
    card_id = card["id"]
    user_inventories[user_id][card_id] = user_inventories[user_id].get(card_id, 0) + 1

    chance_percent = round((card["weight"] / TOTAL_WEIGHT) * 100, 1)
    image_path = os.path.join(BASE_DIR, "images", card["filename"])

    caption = (
        f"<b>{user_name}</b>,\n"
        f"🔎 Вы нашли карточку «<b>{card['title']}</b>»!\n\n"
        f"✨ <b>Редкость:</b> {card['rarity']}\n"
        f"📊 <b>Шанс выпадения:</b> {chance_percent}%\n\n"
        f"📦 Карта добавлена в ваш инвентарь!"
    )
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await message.answer_photo(photo=photo, caption=caption, parse_mode="HTML", reply_markup=get_main_keyboard())
    else:
        await message.answer(f"⚠️ Файл {card['filename']} не найден!\n\n{caption}", parse_mode="HTML", reply_markup=get_main_keyboard())

# --- ЛОГИКА ИНВЕНТАРЯ ---
async def perform_inventory(user_id: int, user_name: str, message: types.Message):
    if user_id not in user_inventories or not user_inventories[user_id]:
        await message.answer(
            f"📦 <b>{user_name}</b>, ваш инвентарь пуст!\n"
            f"Нажмите кнопку ниже, чтобы найти первую карточку.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return

    user_cards = user_inventories[user_id]
    total_found = sum(user_cards.values())
    
    text = f"🎒 <b>Инвентарь {user_name}:</b>\n"
    text += f"Всего найдено карт: <b>{total_found}</b>\n\n"

    for card in CARDS:
        card_id = card["id"]
        if card_id in user_cards:
            count = user_cards[card_id]
            chance_percent = round((card["weight"] / TOTAL_WEIGHT) * 100, 1)
            text += (
                f"• <b>{card['title']}</b> — {count} шт.\n"
                f"  └ Редкость: {card['rarity']} ({chance_percent}%)\n"
            )

    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())

# --- ОБРАБОТКА КОМАНД ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, <b>{message.from_user.first_name}</b>! Выбери действие:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@dp.message(Command("cdfind"))
async def cmd_find_msg(message: types.Message):
    await perform_find(message.from_user.id, message.from_user.first_name, message)

@dp.message(Command("inventory"))
async def cmd_inventory_msg(message: types.Message):
    await perform_inventory(message.from_user.id, message.from_user.first_name, message)

# --- ОБРАБОТКА ИНЛАЙН-КНОПОК ---
@dp.callback_query(F.data == "action_find")
async def cb_find(callback: types.CallbackQuery):
    await callback.answer()
    await perform_find(callback.from_user.id, callback.from_user.first_name, callback.message)

@dp.callback_query(F.data == "action_inventory")
async def cb_inventory(callback: types.CallbackQuery):
    await callback.answer()
    await perform_inventory(callback.from_user.id, callback.from_user.first_name, callback.message)

# --- ГЛАВНАЯ ТОЧКА ВХОДА ---
async def main():
    await set_main_menu(bot)
    await start_website()  # Запуск веб-сервера для Render
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
