import os
import logging
import asyncio
import httpx

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

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

OWNER_ID = 610625282
CHANNEL = "@F1cklock"

PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

AI_MODEL = "gemini-3.7-flash"

schedule = []

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


def is_owner(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id == OWNER_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Панель управления F1cklock:",
        reply_markup=MENU,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "❌ Отменено.",
        reply_markup=MENU,
    )


async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "post"

    await update.message.reply_text(
        "📝 Отправь текст, фото, видео или файл.\n\n"
        "Я опубликую его в канал.",
        reply_markup=CANCEL,
    )


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "announce"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "🎮 Какая игра?",
        reply_markup=CANCEL,
    )


async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "live"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "🎮 Во что играем?",
        reply_markup=CANCEL,
    )


async def clip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["mode"] = "clip"

    await update.message.reply_text(
        "🎬 Отправь клип.",
        reply_markup=CANCEL,
    )


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


async def handle_schedule_game(update, context):
    context.user_data["game"] = update.message.text
    context.user_data["step"] = "day"

    await update.message.reply_text(
        "📅 В какой день стрим?",
        reply_markup=CANCEL,
    )


async def handle_schedule_day(update, context):
    context.user_data["day"] = update.message.text
    context.user_data["step"] = "time"

    await update.message.reply_text(
        "⏰ Во сколько?",
        reply_markup=CANCEL,
    )


async def handle_schedule_time(update, context):
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


async def generate_with_gemini(prompt: str):
    logging.info("Gemini REST request started")

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{AI_MODEL}:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Ты SMM-помощник Telegram-канала F1cklock.\n"
                            "Пиши короткие, живые и энергичные посты "
                            "для игрового канала и стримов.\n"
                            "Не используй длинные вступления.\n"
                            "Используй эмодзи умеренно.\n"
                            "Не добавляй пояснения от себя.\n\n"
                            f"Задача пользователя:\n{prompt}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 500,
        },
    }

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    delays = [5, 15, 30]

    for attempt in range(4):
        try:
            timeout = httpx.Timeout(
                connect=10.0,
                read=35.0,
                write=10.0,
                pool=10.0,
            )

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

            logging.info(
                "Gemini REST HTTP status: %s",
                response.status_code,
            )

            if response.status_code == 503:
                if attempt < 3:
                    logging.warning(
                        "Gemini 503. Retry in %s seconds.",
                        delays[attempt],
                    )

                    await asyncio.sleep(delays[attempt])
                    continue

                logging.error(
                    "Gemini still unavailable after 4 attempts."
                )

                raise RuntimeError("Gemini HTTP 503")

            if response.status_code != 200:
                logging.error(
                    "Gemini REST error: %s",
                    response.text[:1000],
                )

                raise RuntimeError(
                    f"Gemini HTTP {response.status_code}"
                )

            data = response.json()

            try:
                text = (
                    data["candidates"][0]
                    ["content"]["parts"][0]["text"]
                )
            except (KeyError, IndexError, TypeError):
                logging.error(
                    "Unexpected Gemini response: %s",
                    data,
                )

                raise RuntimeError(
                    "Не удалось получить текст Gemini"
                )

            logging.info(
                "Gemini REST request completed"
            )

            return text

        except httpx.TimeoutException:
            if attempt < 3:
                logging.warning(
                    "Gemini timeout. Retry in %s seconds.",
                    delays[attempt],
                )

                await asyncio.sleep(delays[attempt])
                continue

            logging.exception(
                "Gemini timeout after all attempts"
            )

            raise


async def generate_ai(update, context):
    prompt = update.message.text

    await update.message.reply_text(
        "🤖 Генерирую...\n\n"
        "Обычно это занимает несколько секунд.",
        reply_markup=CANCEL,
    )

    try:
        text = await generate_with_gemini(prompt)

        text = (text or "").strip()

        if not text:
            raise RuntimeError(
                "Gemini вернул пустой ответ"
            )

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

    except httpx.TimeoutException:
        logging.exception(
            "Gemini REST timeout"
        )

        context.user_data.clear()

        await update.message.reply_text(
            "⏱ Gemini не ответил вовремя.\n\n"
            "Попробуй ещё раз.",
            reply_markup=MENU,
        )

    except Exception:
        logging.exception(
            "Gemini REST error"
        )

        context.user_data.clear()

        await update.message.reply_text(
            "❌ Ошибка Gemini.\n\n"
            "Попробуй ещё раз.",
            reply_markup=MENU,
        )


async def ai_buttons(update, context):
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
            logging.exception(
                "AI publication error"
            )

            await query.edit_message_text(
                "❌ Не удалось опубликовать."
            )

    elif action == "ai_retry":
        old_prompt = context.user_data.get(
            "ai_prompt"
        )

        if not old_prompt:
            await query.edit_message_text(
                "❌ Не удалось повторить генерацию."
            )
            return

        await query.edit_message_text(
            "🔄 Генерирую новый вариант..."
        )

        try:
            retry_prompt = (
                "Создай НОВЫЙ вариант.\n"
                "Он должен отличаться от предыдущего.\n\n"
                f"Задача пользователя:\n{old_prompt}"
            )

            text = await generate_with_gemini(
                retry_prompt
            )

            text = (text or "").strip()

            if not text:
                raise RuntimeError(
                    "Gemini вернул пустой ответ"
                )

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

        except httpx.TimeoutException:
            context.user_data.clear()

            await query.message.reply_text(
                "⏱ Gemini не ответил вовремя.",
                reply_markup=MENU,
            )

        except Exception:
            logging.exception(
                "Gemini retry error"
            )

            context.user_data.clear()

            await query.message.reply_text(
                "❌ Не удалось создать новый вариант.",
                reply_markup=MENU,
            )


async def settings(update, context):
    await update.message.reply_text(
        "⚙️ Настройки\n\n"
        "Пока доступны настройки по умолчанию.",
        reply_markup=MENU,
    )


async def publish_media(update, context):
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
        logging.exception(
            "Publication error"
        )

        await update.message.reply_text(
            "❌ Ошибка публикации.",
            reply_markup=MENU,
        )


async def handle_message(update, context):
    if not is_owner(update):
        return

    message = update.message

    if not message:
        return

    text = message.text

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

    if context.user_data.get("mode") == "ai":
        if message.text:
            await generate_ai(
                update,
                context,
            )
        return

    if context.user_data.get("mode") == "add_stream":
        step = context.user_data.get("step")

        if step == "game":
            if not message.text:
                await update.message.reply_text(
                    "🎮 Напиши название игры текстом.",
                    reply_markup=CANCEL,
                )
                return

            await handle_schedule_game(
                update,
                context,
            )
            return

        if step == "day":
            await handle_schedule_day(
                update,
                context,
            )
            return

        if step == "time":
            await handle_schedule_time(
                update,
                context,
            )
            return

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

    if mode in [
        "post",
        "clip",
        "announce",
        "live",
    ]:
        await publish_media(
            update,
            context,
        )
        return


def main():
    logging.basicConfig(
        format=(
            "%(asctime)s - "
            "%(levelname)s - "
            "%(message)s"
        ),
        level=logging.INFO,
    )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

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

    print(
        "F1cklock bot starting with webhook..."
    )

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        allowed_updates=Update.ALL_TYPES,
    )


if __name__ == "__main__":
    main()
