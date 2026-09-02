import os
import logging

from google import genai

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

OWNER_ID = 610625282
CHANNEL = "@F1cklock"

PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

AI_MODEL = "gemini-3.7-flash"

ai = genai.Client(api_key=GEMINI_API_KEY)

# Расписание хранится в памяти процесса.
schedule = []


# =========================
# КЛАВИАТУРЫ
# =========================

MENU = ReplyKeyboardMarkup(
    [
        ["🎮 Создать пост", "🔴 Анонс стрима"],
        ["📡 Я в эфире", "📅 Расписание"],
        ["🎬 Клип", "🤖 Создать с ИИ"],
        ["⚙️ Настройки"],
    ],
    resize_keyboard=True,
)

CANCEL = ReplyKeyboardMarkup(
    [["❌ Отмена"]],
    resize_keyboard=True,
)

SCHEDULE_MENU = ReplyKeyboardMarkup(
    [
        ["➕ Добавить стрим"],
        ["📋 Показать расписание"],
        ["⬅️ Главное меню"],
    ],
    resize_keyboard=True,
)


# =========================
# ПРОВЕРКА ВЛАДЕЛЬЦА
# =========================

def is_owner(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id == OWNER_ID)


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Панель управления F1cklock:",
        reply_markup=MENU,
    )


# =========================
# ОТМЕНА
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Отменено.",
        reply_markup=MENU,
    )


# =========================
# СОЗДАТЬ ПОСТ
# =========================

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "post"

    await update.message.reply_text(
        "📝 Отправь текст, фото, видео или файл.\n\n"
        "Я опубликую его в канал.",
        reply_markup=CANCEL,
    )


# =========================
# АНОНС
# =========================

async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "announce"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "🎮 Какая игра?",
        reply_markup=CANCEL,
    )


# =========================
# Я В ЭФИРЕ
# =========================

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "live"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "🎮 Во что играем?",
        reply_markup=CANCEL,
    )


# =========================
# КЛИП
# =========================

async def clip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "clip"

    await update.message.reply_text(
        "🎬 Отправь клип.",
        reply_markup=CANCEL,
    )


# =========================
# РАСПИСАНИЕ
# =========================

async def schedule_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "📅 Расписание стримов:",
        reply_markup=SCHEDULE_MENU,
    )


async def add_stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "add_stream"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "🎮 Какая игра?",
        reply_markup=CANCEL,
    )


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not schedule:
        await update.message.reply_text(
            "📅 Расписание пока пустое.",
            reply_markup=SCHEDULE_MENU,
        )
        return

    text = "📅 РАСПИСАНИЕ\n\n"

    for i, item in enumerate(schedule, 1):
        text += (
            f"{i}. 🎮 {item['game']}\n"
            f"📅 {item['day']}\n"
            f"⏰ {item['time']}\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=SCHEDULE_MENU,
    )


# =========================
# ДОБАВЛЕНИЕ СТРИМА
# =========================

async def handle_schedule_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["game"] = update.message.text
    context.user_data["step"] = "day"

    await update.message.reply_text(
        "📅 В какой день стрим?",
        reply_markup=CANCEL,
    )


async def handle_schedule_day(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["day"] = update.message.text
    context.user_data["step"] = "time"

    await update.message.reply_text(
        "⏰ Во сколько?",
        reply_markup=CANCEL,
    )


async def handle_schedule_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    game = context.user_data["game"]
    day = context.user_data["day"]
    time = update.message.text

    schedule.append(
        {
            "game": game,
            "day": day,
            "time": time,
        }
    )

    await update.message.reply_text(
        f"✅ Стрим добавлен!\n\n"
        f"🎮 {game}\n"
        f"📅 {day}\n"
        f"⏰ {time}",
        reply_markup=SCHEDULE_MENU,
    )

    # Автоматический анонс в канал
    try:
        await context.bot.send_message(
            chat_id=CHANNEL,
            text=(
                "🔴 СКОРО СТРИМ!\n\n"
                f"🎮 {game}\n"
                f"📅 {day}\n"
                f"⏰ {time}\n\n"
                "🔥 Залетаем!"
            ),
        )
    except Exception:
        logging.exception("Schedule announcement error")

    context.user_data.clear()


# =========================
# ИИ
# =========================

async def ai_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "ai"

    await update.message.reply_text(
        "🤖 Что нужно создать?\n\n"
        "Напиши обычным текстом.\n\n"
        "Например:\n"
        "«Сделай дерзкий анонс CS2 сегодня в 20:00»",
        reply_markup=CANCEL,
    )


async def generate_ai(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    prompt = update.message.text

    await update.message.reply_text(
        "🤖 Генерирую...\n\n"
        "Обычно это занимает несколько секунд.",
        reply_markup=CANCEL,
    )

    try:
        response = await ai.aio.models.generate_content(
            model=AI_MODEL,
            contents=(
                "Ты SMM-помощник Telegram-канала F1cklock.\n"
                "Пиши короткие, живые, энергичные посты "
                "для игрового канала и стримов.\n"
                "Не используй длинные вступления.\n"
                "Используй эмодзи умеренно.\n"
                "Не добавляй пояснения от себя.\n\n"
                f"Задача пользователя:\n{prompt}"
            ),
        )

        text = (response.text or "").strip()

        if not text:
            raise RuntimeError("Gemini вернул пустой ответ")

        context.user_data["ai_text"] = text
        context.user_data["ai_prompt"] = prompt

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Опубликовать",
                        callback_data="ai_publish",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔄 Переделать",
                        callback_data="ai_retry",
                    ),
                    InlineKeyboardButton(
                        "❌ Отмена",
                        callback_data="ai_cancel",
                    ),
                ],
            ]
        )

        await update.message.reply_text(
            "🤖 Готово:\n\n" + text,
            reply_markup=keyboard,
        )

    except Exception:
        logging.exception("Gemini error")

        await update.message.reply_text(
            "❌ Gemini не ответил.\n\n"
            "Проверь настройки GEMINI_API_KEY в Render.",
            reply_markup=MENU,
        )

        context.user_data.clear()


# =========================
# КНОПКИ ИИ
# =========================

async def ai_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query.from_user.id != OWNER_ID:
        await query.answer()
        return

    await query.answer()

    action = query.data

    if action == "ai_cancel":
        context.user_data.clear()

        await query.edit_message_text(
            "❌ Отменено."
        )

        await query.message.reply_text(
            "Главное меню:",
            reply_markup=MENU,
        )

    elif action == "ai_publish":
        text = context.user_data.get("ai_text")

        if not text:
            await query.edit_message_text(
                "❌ Текст не найден."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=text,
            )

            await query.edit_message_text(
                "✅ Опубликовано в канал!"
            )

            context.user_data.clear()

            await query.message.reply_text(
                "Главное меню:",
                reply_markup=MENU,
            )

        except Exception:
            logging.exception("AI publication error")

            await query.edit_message_text(
                "❌ Не удалось опубликовать."
            )

    elif action == "ai_retry":
        old_prompt = context.user_data.get("ai_prompt")

        if not old_prompt:
            await query.edit_message_text(
                "❌ Не удалось повторить генерацию."
            )
            return

        await query.edit_message_text(
            "🔄 Генерирую новый вариант..."
        )

        try:
            response = await ai.aio.models.generate_content(
                model=AI_MODEL,
                contents=(
                    "Ты SMM-помощник Telegram-канала F1cklock.\n"
                    "Создай НОВЫЙ вариант поста.\n"
                    "Он должен отличаться от предыдущего.\n"
                    "Пиши коротко, живо и энергично.\n"
                    "Используй эмодзи умеренно.\n"
                    "Не добавляй пояснения.\n\n"
                    f"Задача пользователя:\n{old_prompt}"
                ),
            )

            text = (response.text or "").strip()

            if not text:
                raise RuntimeError("Gemini вернул пустой ответ")

            context.user_data["ai_text"] = text

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Опубликовать",
                            callback_data="ai_publish",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "🔄 Переделать",
                            callback_data="ai_retry",
                        ),
                        InlineKeyboardButton(
                            "❌ Отмена",
                            callback_data="ai_cancel",
                        ),
                    ],
                ]
            )

            await query.message.reply_text(
                "🤖 Новый вариант:\n\n" + text,
                reply_markup=keyboard,
            )

        except Exception:
            logging.exception("Gemini retry error")

            context.user_data.clear()

            await query.message.reply_text(
                "❌ Не удалось создать новый вариант.",
                reply_markup=MENU,
            )


# =========================
# НАСТРОЙКИ
# =========================

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ Настройки\n\n"
        "Пока доступны настройки по умолчанию.\n\n"
        "В следующих версиях сюда можно добавить "
        "Twitch, YouTube, Telegram и стиль публикаций.",
        reply_markup=MENU,
    )


# =========================
# ПУБЛИКАЦИЯ МЕДИА
# =========================

async def publish_media(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    try:
        await context.bot.copy_message(
            chat_id=CHANNEL,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id,
        )

        await update.message.reply_text(
            "✅ Опубликовано в канал!",
            reply_markup=MENU,
        )

        context.user_data.clear()

    except Exception:
        logging.exception("Publication error")

        await update.message.reply_text(
            "❌ Ошибка публикации.",
            reply_markup=MENU,
        )


# =========================
# ОБРАБОТКА СООБЩЕНИЙ
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_owner(update):
        return

    message = update.message

    if not message:
        return

    text = message.text

    # Главное меню
    if text == "🎮 Создать пост":
        await create_post(update, context)
        return

    if text == "🔴 Анонс стрима":
        await announce(update, context)
        return

    if text == "📡 Я в эфире":
        await live(update, context)
        return

    if text == "📅 Расписание":
        await schedule_menu(update, context)
        return

    if text == "🎬 Клип":
        await clip(update, context)
        return

    if text == "🤖 Создать с ИИ":
        await ai_menu(update, context)
        return

    if text == "⚙️ Настройки":
        await settings(update, context)
        return

    if text == "❌ Отмена":
        await cancel(update, context)
        return

    if text == "➕ Добавить стрим":
        await add_stream(update, context)
        return

    if text == "📋 Показать расписание":
        await show_schedule(update, context)
        return

    if text == "⬅️ Главное меню":
        context.user_data.clear()

        await update.message.reply_text(
            "Главное меню:",
            reply_markup=MENU,
        )
        return

    # -------------------------
    # ИИ
    # -------------------------

    if context.user_data.get("mode") == "ai":
        if message.text:
            await generate_ai(update, context)
        return

    # -------------------------
    # Расписание
    # -------------------------

    if context.user_data.get("mode") == "add_stream":
        step = context.user_data.get("step")

        if step == "game":
            if not message.text:
                await update.message.reply_text(
                    "🎮 Напиши название игры текстом.",
                    reply_markup=CANCEL,
                )
                return

            await handle_schedule_game(update, context)
            return

        if step == "day":
            await handle_schedule_day(update, context)
            return

        if step == "time":
            await handle_schedule_time(update, context)
            return

    # -------------------------
    # Игровые режимы
    # -------------------------

    mode = context.user_data.get("mode")
    step = context.user_data.get("step")

    if step == "game":
        if not message.text:
            await update.message.reply_text(
                "🎮 Напиши название игры текстом.",
                reply_markup=CANCEL,
            )
            return

        context.user_data["game"] = message.text
        context.user_data["step"] = "content"

        await update.message.reply_text(
            "📝 Теперь отправь текст, фото или видео.",
            reply_markup=CANCEL,
        )
        return

    # -------------------------
    # Контент
    # -------------------------

    if mode in ["post", "clip", "announce", "live"]:
        await publish_media(update, context)
        return


# =========================
# ЗАПУСК
# =========================

def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(
            ai_buttons,
            pattern="^ai_",
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ALL,
            handle_message,
        )
    )

    print("F1cklock bot starting with webhook...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
