import os
import logging

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNER_ID = 610625282
CHANNEL = "@F1cklock"

PORT = int(os.environ.get("PORT", "10000"))
WEBHOOK_URL = os.environ["WEBHOOK_URL"]


# =========================
# КЛАВИАТУРА
# =========================

MENU = ReplyKeyboardMarkup(
    [
        ["🎮 Создать пост", "🔴 Анонс стрима"],
        ["📡 Я в эфире", "📅 Расписание"],
        ["🎬 Клип"],
    ],
    resize_keyboard=True,
)


CANCEL = ReplyKeyboardMarkup(
    [
        ["❌ Отмена"],
    ],
    resize_keyboard=True,
)


# =========================
# МЕНЮ
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user or user.id != OWNER_ID:
        return

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Выбери, что хочешь сделать:",
        reply_markup=MENU,
    )


# =========================
# СОЗДАТЬ ПОСТ
# =========================

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "post"

    await update.message.reply_text(
        "📝 Отправь текст, фото, видео или файл.\n\n"
        "Я сразу опубликую это в канал.",
        reply_markup=CANCEL,
    )


# =========================
# АНОНС СТРИМА
# =========================

async def stream_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "announce"
    context.user_data["step"] = "game"

    await update.message.reply_text(
        "🎮 Какая игра?",
        reply_markup=CANCEL,
    )


# =========================
# Я В ЭФИРЕ
# =========================

async def live_stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    context.user_data["mode"] = "clip"
    context.user_data["step"] = "content"

    await update.message.reply_text(
        "🎬 Отправь клип.\n\n"
        "Я опубликую его в канал.",
        reply_markup=CANCEL,
    )


# =========================
# РАСПИСАНИЕ
# =========================

async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 Расписание\n\n"
        "Функция расписания пока в разработке.",
        reply_markup=MENU,
    )


# =========================
# ОТМЕНА
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ Отменено.\n\n"
        "Выбери действие:",
        reply_markup=MENU,
    )


# =========================
# ОБРАБОТКА ИГРЫ
# =========================

async def handle_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = update.message.text

    context.user_data["game"] = game
    context.user_data["step"] = "content"

    mode = context.user_data.get("mode")

    if mode == "announce":
        text = (
            f"🔴 АНОНС СТРИМА\n\n"
            f"🎮 Игра: {game}\n\n"
            f"📝 Теперь отправь текст, фото или видео для анонса."
        )

    else:
        text = (
            f"📡 Я В ЭФИРЕ\n\n"
            f"🎮 Игра: {game}\n\n"
            f"📝 Теперь отправь текст, фото или видео."
        )

    await update.message.reply_text(
        text,
        reply_markup=CANCEL,
    )


# =========================
# ПУБЛИКАЦИЯ
# =========================

async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    game = context.user_data.get("game")

    try:

        # Обычный пост
        if mode == "post":
            await context.bot.copy_message(
                chat_id=CHANNEL,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id,
            )

        # Клип
        elif mode == "clip":
            await context.bot.copy_message(
                chat_id=CHANNEL,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id,
            )

        # Анонс стрима
        elif mode == "announce":

            await context.bot.send_message(
                chat_id=CHANNEL,
                text=(
                    f"🔴 АНОНС СТРИМА\n\n"
                    f"🎮 {game}"
                ),
            )

            await context.bot.copy_message(
                chat_id=CHANNEL,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id,
            )

        # Я в эфире
        elif mode == "live":

            await context.bot.send_message(
                chat_id=CHANNEL,
                text=(
                    f"📡 Я В ЭФИРЕ\n\n"
                    f"🎮 {game}"
                ),
            )

            await context.bot.copy_message(
                chat_id=CHANNEL,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id,
            )

        else:
            return

        await update.message.reply_text(
            "✅ Опубликовано в канал!",
            reply_markup=MENU,
        )

        context.user_data.clear()

    except Exception:
        logging.exception("Publication error")

        await update.message.reply_text(
            "❌ Не удалось опубликовать. Проверь права бота в канале.",
            reply_markup=MENU,
        )


# =========================
# ОСНОВНОЙ ОБРАБОТЧИК
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not user or user.id != OWNER_ID:
        return

    message = update.message

    if not message:
        return

    text = message.text

    # Кнопки меню
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
        await schedule(update, context)
        return

    if text == "🎬 Клип":
        await clip(update, context)
        return

    if text == "❌ Отмена":
        await cancel(update, context)
        return

    mode = context.user_data.get("mode")
    step = context.user_data.get("step")

    # Если бот ждёт название игры
    if step == "game":
        if not message.text:
            await message.reply_text(
                "🎮 Напиши название игры текстом.",
                reply_markup=CANCEL,
            )
            return

        await handle_game(update, context)
        return

    # Если бот ждёт контент
    if step == "content":
        await publish(update, context)
        return

    # Если выбран обычный пост
    if mode == "post":
        await publish(update, context)
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

    app.add_handler(CommandHandler("start", start))

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
