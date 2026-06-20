import os
import json
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# =========================
# CONFIG
# =========================

API_TOKEN = ""

SUPPORT_GROUP_ID = -1003935131630

SUPER_ADMINS = [686768325]

# =========================
# LOGGING
# =========================

logging.basicConfig(level=logging.INFO)

# =========================
# BOT INIT
# =========================

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")

# =========================
# FILES
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

USERS_FILE = os.path.join(BASE_DIR, "users.json")
REMINDERS_FILE = os.path.join(BASE_DIR, "reminders.json")
SUPPORT_FILE = os.path.join(BASE_DIR, "support.json")

# =========================
# LOAD / SAVE
# =========================

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

users_data = load_json(USERS_FILE, {})
reminders_data = load_json(REMINDERS_FILE, [])
support_data = load_json(SUPPORT_FILE, [])

# =========================
# HELPERS
# =========================

def is_super_admin(user_id):
    return int(user_id) in SUPER_ADMINS

# =========================
# KEYBOARD
# =========================

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🛠 Підтримка")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# =========================
# REMINDER
# =========================

async def send_reminder(chat_id: int, text: str):
    await bot.send_message(chat_id, f"⏰ Нагадування:\n\n{text}")

# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: types.Message):

    user_id = str(message.from_user.id)

    if user_id not in users_data:
        users_data[user_id] = {
            "name": message.from_user.full_name
        }
        save_json(USERS_FILE, users_data)

    await message.answer(
        "👋 Вітаю!\n\n"
        "Формат нагадування:\n"
        "/remind s10 Текст\n\n"
        "Підтримка доступна через кнопку нижче 👇",
        reply_markup=get_main_keyboard()
    )

# =========================
# ADMIN PANEL
# =========================

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):

    if not is_super_admin(message.from_user.id):
        return

    await message.answer(
        "👑 Адмін панель\n\n"
        "/users - список користувачів\n"
        "/supportlist - список звернень\n"
        "/close ID - закрити звернення\n"
        "/broadcast текст - розсилка"
    )

# =========================
# REMIND
# =========================

@dp.message(Command("remind"))
async def remind(message: types.Message):

    args = message.text.split(maxsplit=2)

    if len(args) < 3:
        return await message.answer(
            "❌ Формат:\n/remind s10 Текст"
        )

    time_input = args[1].lower()
    text = args[2]

    try:

        unit = time_input[0]
        num = int(time_input[1:])

        if unit == "s":
            delta = timedelta(seconds=num)

        elif unit == "m":
            delta = timedelta(minutes=num)

        elif unit == "h":
            delta = timedelta(hours=num)

        elif unit == "d":
            delta = timedelta(days=num)

        else:
            return await message.answer("❌ Невірний формат часу")

        run_date = datetime.now() + delta

        scheduler.add_job(
            send_reminder,
            trigger="date",
            run_date=run_date,
            args=(message.chat.id, text)
        )

        reminders_data.append({
            "user_id": message.from_user.id,
            "text": text,
            "time": str(run_date)
        })

        save_json(REMINDERS_FILE, reminders_data)

        await message.answer(
            f"✅ Нагадування створено\n\n"
            f"⏰ Через: {time_input}\n"
            f"📝 Текст: {text}"
        )

    except:
        await message.answer("❌ Помилка формату")

# =========================
# SUPPORT
# =========================

class SupportState(StatesGroup):
    waiting = State()

@dp.message(F.text == "🛠 Підтримка")
async def support_start(message: types.Message, state: FSMContext):

    await state.set_state(SupportState.waiting)

    await message.answer(
        "✍️ Напишіть вашу проблему одним повідомленням"
    )

@dp.message(SupportState.waiting)
async def support_send(message: types.Message, state: FSMContext):

    report_id = len(support_data) + 1

    support_data.append({
        "id": report_id,
        "user_id": message.from_user.id,
        "name": message.from_user.full_name,
        "text": message.text,
        "status": "open",
        "time": str(datetime.now())
    })

    save_json(SUPPORT_FILE, support_data)

    await bot.send_message(
        SUPPORT_GROUP_ID,
        f"🛠 Нове звернення\n\n"
        f"📌 ID: {report_id}\n"
        f"👤 {message.from_user.full_name}\n"
        f"🆔 {message.from_user.id}\n\n"
        f"💬 {message.text}"
    )

    await message.answer("✅ Ваше звернення відправлено")
    await state.clear()

# =========================
# USERS
# =========================

@dp.message(Command("users"))
async def users(message: types.Message):

    if not is_super_admin(message.from_user.id):
        return

    text = "👥 Користувачі:\n\n"

    for user_id, data in users_data.items():
        text += f"{data['name']} | {user_id}\n"

    await message.answer(text[:4000])

# =========================
# SUPPORT LIST
# =========================

@dp.message(Command("supportlist"))
async def supportlist(message: types.Message):

    if not is_super_admin(message.from_user.id):
        return

    if not support_data:
        return await message.answer("❌ Звернень немає")

    text = "🛠 Список звернень:\n\n"

    for s in support_data:

        status = "🟢 OPEN" if s["status"] == "open" else "🔴 CLOSED"

        text += (
            f"📌 ID: {s['id']}\n"
            f"👤 {s['name']}\n"
            f"🆔 {s['user_id']}\n"
            f"{status}\n"
            f"💬 {s['text']}\n\n"
        )

    await message.answer(text[:4000])

# =========================
# CLOSE REPORT
# =========================

@dp.message(Command("close"))
async def close_report(message: types.Message):

    if not is_super_admin(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 2:
        return await message.answer(
            "❌ Формат:\n/close ID"
        )

    try:
        report_id = int(args[1])

    except:
        return await message.answer("❌ ID має бути числом")

    found = False

    for report in support_data:

        if report["id"] == report_id:

            found = True
            report["status"] = "closed"

            save_json(SUPPORT_FILE, support_data)

            try:
                await bot.send_message(
                    report["user_id"],
                    "✅ Ваше звернення було закрито адміністрацією"
                )
            except:
                pass

            await message.answer("✅ Звернення закрито")
            break

    if not found:
        await message.answer("❌ Звернення не знайдено")

# =========================
# BROADCAST
# =========================

@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):

    if not is_super_admin(message.from_user.id):
        return

    text = message.text.replace("/broadcast", "").strip()

    if not text:
        return await message.answer(
            "❌ Формат:\n/broadcast текст"
        )

    count = 0

    for user_id in users_data:

        try:
            await bot.send_message(int(user_id), text)
            count += 1

        except:
            pass

    await message.answer(
        f"✅ Розсилка завершена\n\n"
        f"👥 Отримали: {count}"
    )

# =========================
# RUN
# =========================

async def main():

    scheduler.start()

    print("BOT STARTED")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
