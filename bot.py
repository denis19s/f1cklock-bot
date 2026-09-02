import os
import asyncio
import logging
from datetime import datetime

import httpx
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

CHANNEL = "@F1cklock"
OWNER_ID = 610625282

# Основная и запасная модели Gemini
AI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
]

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# =========================
# КЛАВИАТУРЫ
# =========================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🎮 Создать пост", "🔴 Анонс стрима"],
        ["📡 Я в эфире", "📅 Расписание"],
        ["🎬 Клип", "🤖 Создать с ИИ"],
        ["⚙️ Настройки"],
    ],
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

CANCEL_MENU = ReplyKeyboardMarkup(
    [["❌ Отмена"]],
    resize_keyboard=True,
)

# =========================
# ПРОВЕРКА ВЛАДЕЛЬЦА
# =========================

def is_owner(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id == OWNER_ID)


# =========================
# GEMINI
# =========================

async def generate_ai_text(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY не задан")

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 500
        },
    }

    timeout = httpx.Timeout(
        connect=10.0,
        read=30.0,
        write=10.0,
        pool=10.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:

        for model_index, model in enumerate(AI_MODELS):
            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{model}:generateContent"
            )

            try:
                logger.info("Gemini request started: %s", model)

                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

                logger.info(
                    "Gemini response: model=%s status=%s",
                    model,
                    response.status_code,
                )

                if response.status_code == 200:
                    data = response.json()

                    candidates = data.get("candidates", [])

                    if not candidates:
                        raise RuntimeError(
                            f"Gemini {model}: нет candidates"
                        )

                    parts = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [])
                    )

                    text_parts = []

                    for part in parts:
                        text = part.get("text")
                        if text:
                            text_parts.append(text)

                    result = "\n".join(text_parts).strip()

                    if result:
                        logger.info(
                            "Gemini success: %s",
                            model,
                        )
                        return result

                    raise RuntimeError(
                        f"Gemini {model}: пустой ответ"
                    )

                # Временные ошибки — пробуем следующую модель
                if response.status_code in (
                    429,
                    500,
                    502,
                    503,
                    504,
                ):
                    logger.warning(
                        "Gemini temporary error: model=%s status=%s",
                        model,
                        response.status_code,
                    )

                    if model_index < len(AI_MODELS) - 1:
                        await asyncio.sleep(2)
                        continue

                    raise RuntimeError(
                        f"Gemini временно недоступен: "
                        f"HTTP {response.status_code}"
                    )

                # Ошибка ключа или запроса
                logger.error(
                    "Gemini error: model=%s status=%s body=%s",
                    model,
                    response.status_code,
                    response.text[:500],
                )

                raise RuntimeError(
                    f"Gemini HTTP {response.status_code}"
                )

            except httpx.TimeoutException:
                logger.warning(
                    "Gemini timeout: %s",
                    model,
                )

                if model_index < len(AI_MODELS) - 1:
                    await asyncio.sleep(2)
                    continue

                raise RuntimeError(
                    "Gemini не ответил вовремя"
                )

            except httpx.HTTPError as e:
                logger.warning(
                    "Gemini HTTP error: model=%s error=%s",
                    model,
                    e,
                )

                if model_index < len(AI_MODELS) - 1:
                    await asyncio.sleep(2)
                    continue

                raise RuntimeError(
                    "Ошибка соединения с Gemini"
                )

    raise RuntimeError("Gemini не смог сгенерировать ответ")


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я готов публиковать посты в канал.",
        reply_markup=MAIN_MENU,
    )


# =========================
# ПУБЛИКАЦИЯ
# =========================

async def publish_media(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.message

    if not message:
        return

    await context.bot.copy_message(
        chat_id=CHANNEL,
        from_chat_id=message.chat_id,
        message_id=message.message_id,
    )


# =========================
# СОЗДАНИЕ ПОСТА
# =========================

async def create_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["mode"] = "post"

    await update.message.reply_text(
        "🎮 Пришли текст, фото, видео или файл для публикации.",
        reply_markup=CANCEL_MENU,
    )


# =========================
# АНОНС СТРИМА
# =========================

async def stream_announce(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["mode"] = "announce"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "🔴 Напиши название игры/стрима.",
        reply_markup=CANCEL_MENU,
    )


# =========================
# Я В ЭФИРЕ
# =========================

async def live_stream(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["mode"] = "live"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "📡 Напиши название игры/стрима.",
        reply_markup=CANCEL_MENU,
    )


# =========================
# КЛИП
# =========================

async def create_clip(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["mode"] = "clip"

    await update.message.reply_text(
        "🎬 Пришли клип или видео.",
        reply_markup=CANCEL_MENU,
    )


# =========================
# РАСПИСАНИЕ
# =========================

async def schedule_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📅 Расписание:",
        reply_markup=SCHEDULE_MENU,
    )


async def add_stream(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["mode"] = "schedule"
    context.user_data["step"] = "date"

    await update.message.reply_text(
        "📅 Напиши дату и время стрима.\n\n"
        "Например:\n"
        "05.09 20:00",
        reply_markup=CANCEL_MENU,
    )


async def show_schedule(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    schedule = context.bot_data.get("schedule", [])

    if not schedule:
        await update.message.reply_text(
            "📋 Расписание пока пустое.",
            reply_markup=SCHEDULE_MENU,
        )
        return

    text = "📋 Расписание:\n\n"

    for item in schedule:
        text += f"🔴 {item['date']} — {item['game']}\n"

    await update.message.reply_text(
        text,
        reply_markup=SCHEDULE_MENU,
    )


# =========================
# НАСТРОЙКИ
# =========================

async def settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "⚙️ Настройки\n\n"
        "Бот работает в режиме публикации в канал.\n"
        f"Канал: {CHANNEL}",
        reply_markup=MAIN_MENU,
    )


# =========================
# AI
# =========================

async def ai_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["mode"] = "ai"

    await update.message.reply_text(
        "🤖 Напиши тему поста.\n\n"
        "Например:\n"
        "«Сделай пост о сегодняшнем стриме по CS2»",
        reply_markup=CANCEL_MENU,
    )


async def generate_ai_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
):
    waiting = await update.message.reply_text(
        "🤖 Генерирую...\n"
        "Обычно это занимает несколько секунд."
    )

    try:
        ai_prompt = (
            "Ты помогаешь вести Telegram-канал стримера.\n"
            "Создай короткий, живой и привлекательный пост "
            "для Telegram на русском языке.\n\n"
            "Не используй слишком много эмодзи.\n"
            "Не придумывай факты, которых нет в запросе.\n"
            "Пиши сразу готовый текст поста без пояснений.\n\n"
            f"Тема:\n{prompt}"
        )

        text = await generate_ai_text(ai_prompt)

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Опубликовать",
                        callback_data="ai_publish",
                    ),
                    InlineKeyboardButton(
                        "🔄 Переделать",
                        callback_data="ai_retry",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "❌ Отмена",
                        callback_data="ai_cancel",
                    )
                ],
            ]
        )

        context.user_data["ai_text"] = text
        context.user_data["ai_prompt"] = prompt

        await waiting.edit_text(
            "🤖 Готово!\n\n"
            + text,
            reply_markup=keyboard,
        )

    except Exception as e:
        logger.exception("Gemini error")

        await waiting.edit_text(
            "❌ Gemini сейчас не смог ответить.\n\n"
            "Попробуй ещё раз через несколько секунд."
        )


# =========================
# AI КНОПКИ
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

    if query.data == "ai_cancel":
        context.user_data.clear()

        await query.edit_message_text(
            "❌ Отменено."
        )

        await query.message.reply_text(
            "Главное меню:",
            reply_markup=MAIN_MENU,
        )

        return

    if query.data == "ai_publish":
        text = context.user_data.get("ai_text")

        if not text:
            await query.edit_message_text(
                "❌ Текст больше недоступен."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=CHANNEL,
                text=text,
            )

            context.user_data.clear()

            await query.edit_message_text(
                "✅ Опубликовано в канале."
            )

            await query.message.reply_text(
                "Главное меню:",
                reply_markup=MAIN_MENU,
            )

        except Exception:
            logger.exception("Publish error")

            await query.edit_message_text(
                "❌ Не удалось опубликовать пост."
            )

        return

    if query.data == "ai_retry":
        prompt = context.user_data.get("ai_prompt")

        if not prompt:
            await query.edit_message_text(
                "❌ Исходная тема больше недоступна."
            )
            return

        await query.edit_message_text(
            "🔄 Переделываю..."
        )

        try:
            ai_prompt = (
                "Создай другой вариант поста для Telegram "
                "на русском языке.\n"
                "Сделай его живым, коротким и естественным.\n"
                "Не объясняй, что ты сделал — дай только готовый пост.\n\n"
                f"Тема:\n{prompt}"
            )

            text = await generate_ai_text(ai_prompt)

            context.user_data["ai_text"] = text

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Опубликовать",
                            callback_data="ai_publish",
                        ),
                        InlineKeyboardButton(
                            "🔄 Переделать",
                            callback_data="ai_retry",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "❌ Отмена",
                            callback_data="ai_cancel",
                        )
                    ],
                ]
            )

            await query.edit_message_text(
                "🤖 Новый вариант:\n\n" + text,
                reply_markup=keyboard,
            )

        except Exception:
            logger.exception("Gemini retry error")

            await query.edit_message_text(
                "❌ Gemini снова не ответил.\n"
                "Попробуй ещё раз."
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

    text = message.text or ""

    # Отмена
    if text == "❌ Отмена":
        context.user_data.clear()

        await message.reply_text(
            "❌ Отменено.",
            reply_markup=MAIN_MENU,
        )

        return

    # Главное меню
    if text == "🎮 Создать пост":
        await create_post(update, context)
        return

    if text == "🔴 Анонс стрима":
        await stream_announce(update, context)
        return

    if text == "📡 Я в эфире":
        await live_stream(update, context)
        return

    if text == "📅 Расписание":
        await schedule_menu(update, context)
        return

    if text == "🎬 Клип":
        await create_clip(update, context)
        return

    if text == "🤖 Создать с ИИ":
        await ai_start(update, context)
        return

    if text == "⚙️ Настройки":
        await settings(update, context)
        return

    if text == "⬅️ Главное меню":
        context.user_data.clear()

        await message.reply_text(
            "Главное меню:",
            reply_markup=MAIN_MENU,
        )

        return

    if text == "➕ Добавить стрим":
        await add_stream(update, context)
        return

    if text == "📋 Показать расписание":
        await show_schedule(update, context)
        return

    # =====================
    # AI
    # =====================

    if context.user_data.get("mode") == "ai":
        if message.text:
            await generate_ai_post(
                update,
                context,
                message.text,
            )
        return

    # =====================
    # РАСПИСАНИЕ
    # =====================

    if context.user_data.get("mode") == "schedule":
        step = context.user_data.get("step")

        if step == "date":
            context.user_data["date"] = text
            context.user_data["step"] = "game"

            await message.reply_text(
                "🎮 Теперь напиши название игры.",
                reply_markup=CANCEL_MENU,
            )

            return

        if step == "game":
            date = context.user_data.get("date")

            schedule = context.bot_data.setdefault(
                "schedule",
                [],
            )

            schedule.append(
                {
                    "date": date,
                    "game": text,
                }
            )

            context.user_data.clear()

            await message.reply_text(
                "✅ Стрим добавлен в расписание.",
                reply_markup=MAIN_MENU,
            )

            return

    # =====================
    # АНОНС / ЭФИР
    # =====================

    mode = context.user_data.get("mode")
    step = context.user_data.get("step")

    if mode in ("announce", "live"):
        if step == "game":
            context.user_data["game"] = text
            context.user_data["step"] = "content"

            await message.reply_text(
                "📝 Теперь пришли текст, фото или видео "
                "для поста.",
                reply_markup=CANCEL_MENU,
            )

            return

        if step == "content":
            await publish_media(update, context)

            context.user_data.clear()

            await message.reply_text(
                "✅ Опубликовано в канале.",
                reply_markup=MAIN_MENU,
            )

            return

    # =====================
    # ОБЫЧНЫЙ ПОСТ / КЛИП
    # =====================

    if mode in ("post", "clip"):
        await publish_media(update, context)

        context.user_data.clear()

        await message.reply_text(
            "✅ Опубликовано в канале.",
            reply_markup=MAIN_MENU,
        )

        return


# =========================
# АВТОАНОНС РАСПИСАНИЯ
# =========================

async def schedule_checker(
    context: ContextTypes.DEFAULT_TYPE,
):
    schedule = context.bot_data.get("schedule", [])

    if not schedule:
        return

    now = datetime.now().strftime("%d.%m %H:%M")

    for item in schedule[:]:
        if item["date"] == now:
            try:
                await context.bot.send_message(
                    chat_id=CHANNEL,
                    text=(
                        "🔴 СТРИМ НАЧИНАЕТСЯ!\n\n"
                        f"🎮 {item['game']}"
                    ),
                )

                schedule.remove(item)

            except Exception:
                logger.exception(
                    "Schedule announcement error"
                )


# =========================
# ЗАПУСК
# =========================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан")

    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL не задан")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(ai_buttons)
    )

    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            handle_message,
        )
    )

    # Проверка расписания каждую минуту
    application.job_queue.run_repeating(
        schedule_checker,
        interval=60,
        first=10,
    )

    logger.info("Bot starting...")

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
