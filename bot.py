import os
import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.environ["BOT_TOKEN"]

OWNER_ID = 610625282
CHANNEL = "@F1cklock"


async def copy_message_to_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    if user.id != OWNER_ID:
        return

    try:
        await context.bot.copy_message(
            chat_id=CHANNEL,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )

        logging.info("Message copied successfully")

    except Exception:
        logging.exception("Error copying message")


def main():
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND,
            copy_message_to_channel,
        )
    )

    print("F1cklock bot started!")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
