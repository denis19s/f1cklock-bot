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


# =========================================================
# НАСТРОЙКИ
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

CHANNEL = "@F1cklock"
OWNER_ID = 610625282

TWITCH_URL = "https://m.twitch.tv/f1cklock/home"

AI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
]


# =========================================================
# ЛОГИ
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# СТИЛИ
# =========================================================

STYLES = {
    "f1cklock": {
        "name": "✨ F1cklock",
        "prompt": (
            "Фирменный стиль F1cklock: живой, уверенный, "
            "разговорный, современный, с характером. "
            "Не пиши как официальное СМИ."
        ),
    },
    "bold": {
        "name": "🔥 Дерзкий",
        "prompt": (
            "Дерзкий стиль: уверенный, энергичный, "
            "немного провокационный, но без перебора."
        ),
    },
    "funny": {
        "name": "😂 С юмором",
        "prompt": (
            "Стиль с юмором: лёгкая ирония, шутки и "
            "мемный оттенок, но текст должен оставаться понятным."
        ),
    },
    "calm": {
        "name": "😎 Спокойный",
        "prompt": (
            "Спокойный стиль: естественный, приятный, "
            "без лишнего хайпа и большого количества эмодзи."
        ),
    },
    "gaming": {
        "name": "🎮 Игровой",
        "prompt": (
            "Игровой стиль: атмосфера стрима, игры, "
            "геймерский сленг в разумных пределах."
        ),
    },
    "news": {
        "name": "📰 Новостной",
        "prompt": (
            "Новостной стиль: быстро, понятно и по делу. "
            "Главный факт должен быть понятен с первых строк."
        ),
    },
    "toxic": {
        "name": "💀 Токсичный",
        "prompt": (
            "Токсичный игровой стиль: дерзко, саркастично "
            "и с характером, но без оскорблений защищённых групп "
            "и без чрезмерной грубости."
        ),
    },
    "short": {
        "name": "⚡ Очень короткий",
        "prompt": (
            "Очень короткий стиль: максимум смысла в нескольких "
            "строках. Никакой воды."
        ),
    },
}


# =========================================================
# ИГРЫ ДЛЯ НОВОСТЕЙ
# =========================================================

NEWS_GAMES = {
    "cs2": "Counter-Strike 2",
    "gta": "GTA",
    "pubg": "PUBG",
    "fortnite": "Fortnite",
    "minecraft": "Minecraft",
    "dota2": "Dota 2",
    "valorant": "Valorant",
    "other": "Другие игры",
}


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🎮 Создать пост", "🔴 Анонс стрима"],
        ["📡 Я в эфире", "📅 Расписание"],
        ["🎬 Клип", "📰 Новости игр"],
        ["🤖 Создать с ИИ", "⚙️ Настройки"],
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


# =========================================================
# ПРОВЕРКА ВЛАДЕЛЬЦА
# =========================================================

def is_owner(update: Update) -> bool:
    user = update.effective_user

    return bool(
        user and user.id == OWNER_ID
    )


# =========================================================
# TWITCH
# =========================================================

def fix_twitch_link(text: str) -> str:

    replacements = [
        "[ссылка на трансляцию]",
        "[ссылка на стрим]",
        "[ссылка]",
        "<ссылка на трансляцию>",
        "<ссылка на стрим>",
        "ССЫЛКА_НА_ТРАНСЛЯЦИЮ",
        "ССЫЛКА_НА_СТРИМ",
    ]

    for placeholder in replacements:
        text = text.replace(
            placeholder,
            TWITCH_URL,
        )

    return text


# =========================================================
# КЛАВИАТУРА СТИЛЕЙ
# =========================================================

def styles_keyboard(
    prefix="style",
):
    buttons = []

    items = list(
        STYLES.items()
    )

    for i in range(
        0,
        len(items),
        2,
    ):
        row = []

        for key, data in items[i:i + 2]:
            row.append(
                InlineKeyboardButton(
                    data["name"],
                    callback_data=f"{prefix}_{key}",
                )
            )

        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="global_cancel",
            )
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )


# =========================================================
# AI КНОПКИ
# =========================================================

def ai_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🖼️ Добавить фото",
                    callback_data="ai_add_photo",
                ),
                InlineKeyboardButton(
                    "🎨 Сменить стиль",
                    callback_data="ai_change_style",
                ),
            ],
            [
                InlineKeyboardButton(
                    "✏️ Изменить",
                    callback_data="ai_edit",
                ),
            ],
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


def ai_photo_keyboard():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Опубликовать",
                    callback_data="ai_publish",
                ),
                InlineKeyboardButton(
                    "🖼️ Другое фото",
                    callback_data="ai_add_photo",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🎨 Сменить стиль",
                    callback_data="ai_change_style",
                ),
                InlineKeyboardButton(
                    "✏️ Изменить",
                    callback_data="ai_edit",
                ),
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


# =========================================================
# GEMINI
# =========================================================

async def gemini_request(
    prompt: str,
    use_search=False,
) -> str:

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY не задан"
        )

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
            "maxOutputTokens": 800
        },
    }

    # Google Search для новостей
    if use_search:
        payload["tools"] = [
            {
                "google_search": {}
            }
        ]

    timeout = httpx.Timeout(
        connect=10.0,
        read=40.0,
        write=10.0,
        pool=10.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        for model_index, model in enumerate(
            AI_MODELS
        ):

            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{model}:generateContent"
            )

            try:

                logger.info(
                    "Gemini request: model=%s search=%s",
                    model,
                    use_search,
                )

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

                    candidates = data.get(
                        "candidates",
                        [],
                    )

                    if not candidates:
                        raise RuntimeError(
                            "Gemini: нет candidates"
                        )

                    parts = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [])
                    )

                    text_parts = []

                    for part in parts:

                        text = part.get(
                            "text"
                        )

                        if text:
                            text_parts.append(
                                text
                            )

                    result = "\n".join(
                        text_parts
                    ).strip()

                    if result:
                        return fix_twitch_link(
                            result
                        )

                    raise RuntimeError(
                        "Gemini: пустой ответ"
                    )

                if response.status_code in (
                    429,
                    500,
                    502,
                    503,
                    504,
                ):

                    logger.warning(
                        "Gemini temporary error: %s",
                        response.status_code,
                    )

                    if model_index < len(
                        AI_MODELS
                    ) - 1:

                        await asyncio.sleep(
                            2
                        )

                        continue

                    raise RuntimeError(
                        "Gemini временно недоступен"
                    )

                logger.error(
                    "Gemini error: %s",
                    response.status_code,
                )

                raise RuntimeError(
                    f"Gemini HTTP "
                    f"{response.status_code}"
                )

            except httpx.TimeoutException:

                logger.warning(
                    "Gemini timeout: %s",
                    model,
                )

                if model_index < len(
                    AI_MODELS
                ) - 1:

                    await asyncio.sleep(
                        2
                    )

                    continue

                raise RuntimeError(
                    "Gemini не ответил вовремя"
                )

            except httpx.HTTPError as e:

                logger.warning(
                    "Gemini HTTP error: %s",
                    e,
                )

                if model_index < len(
                    AI_MODELS
                ) - 1:

                    await asyncio.sleep(
                        2
                    )

                    continue

                raise RuntimeError(
                    "Ошибка соединения с Gemini"
                )

    raise RuntimeError(
        "Gemini не смог ответить"
    )


# =========================================================
# ГЕНЕРАЦИЯ AI ПОСТА
# =========================================================

async def generate_ai_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
):

    waiting = await update.message.reply_text(
        "🤖 Генерирую..."
    )

    style_key = context.user_data.get(
        "ai_style",
        "f1cklock",
    )

    style = STYLES.get(
        style_key,
        STYLES["f1cklock"],
    )

    try:

        ai_prompt = (
            "Ты помогаешь вести Telegram-канал "
            "стримера F1cklock.\n\n"

            f"Стиль текста:\n"
            f"{style['prompt']}\n\n"

            "Создай готовый пост для Telegram "
            "на русском языке.\n\n"

            "Пост должен быть живым, естественным "
            "и интересным.\n\n"

            "Не используй канцелярит.\n"
            "Не объясняй свою работу.\n"
            "Не придумывай факты.\n"
            "Не используй слишком много эмодзи.\n\n"

            "Если уместно пригласить зрителей "
            "на стрим, используй реальную ссылку:\n"
            f"{TWITCH_URL}\n\n"

            "Никогда не используй заглушки "
            "[ссылка на трансляцию], "
            "[ссылка на стрим] или [ссылка].\n\n"

            "Дай сразу готовый текст поста.\n\n"

            f"Тема:\n{prompt}"
        )

        text = await gemini_request(
            ai_prompt
        )

        context.user_data["ai_text"] = text
        context.user_data["ai_prompt"] = prompt
        context.user_data["ai_photo"] = None
        context.user_data["mode"] = "ai"

        await waiting.edit_text(
            "🤖 Готово!\n\n"
            f"{text}\n\n"
            f"🎨 Стиль: {style['name']}",
            reply_markup=ai_keyboard(),
        )

    except Exception:

        logger.exception(
            "AI generation error"
        )

        await waiting.edit_text(
            "❌ Gemini сейчас не смог ответить.\n\n"
            "Попробуй ещё раз."
        )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not is_owner(update):
        return

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я готов публиковать посты в канал.",
        reply_markup=MAIN_MENU,
    )


# =========================================================
# ОБЫЧНАЯ ПУБЛИКАЦИЯ
# =========================================================

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


# =========================================================
# ОБЫЧНЫЙ ПОСТ
# =========================================================

async def create_post(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data["mode"] = "post"

    await update.message.reply_text(
        "🎮 Пришли текст, фото, видео или файл "
        "для публикации.",
        reply_markup=CANCEL_MENU,
    )


# =========================================================
# АНОНС
# =========================================================

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


# =========================================================
# Я В ЭФИРЕ
# =========================================================

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


# =========================================================
# КЛИП
# =========================================================

async def create_clip(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data["mode"] = "clip"

    await update.message.reply_text(
        "🎬 Пришли клип или видео.",
        reply_markup=CANCEL_MENU,
    )


# =========================================================
# РАСПИСАНИЕ
# =========================================================

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

    schedule = context.bot_data.get(
        "schedule",
        [],
    )

    if not schedule:

        await update.message.reply_text(
            "📋 Расписание пока пустое.",
            reply_markup=SCHEDULE_MENU,
        )

        return

    text = "📋 Расписание:\n\n"

    for item in schedule:

        text += (
            f"🔴 {item['date']} — "
            f"{item['game']}\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=SCHEDULE_MENU,
    )


# =========================================================
# НАСТРОЙКИ
# =========================================================

async def settings(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "⚙️ Настройки\n\n"
        "Бот работает в режиме публикации "
        "в канал.\n\n"
        f"Канал: {CHANNEL}",
        reply_markup=MAIN_MENU,
    )


# =========================================================
# AI СТАРТ
# =========================================================

async def ai_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    context.user_data["mode"] = "ai_choose_style"

    await update.message.reply_text(
        "🎨 Выбери стиль AI-поста:",
        reply_markup=styles_keyboard(),
    )


# =========================================================
# НОВОСТИ — СТАРТ
# =========================================================

async def news_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    context.user_data.clear()

    context.user_data["mode"] = "news_choose_game"

    keyboard = []

    items = list(
        NEWS_GAMES.items()
    )

    for i in range(
        0,
        len(items),
        2,
    ):

        row = []

        for key, name in items[i:i + 2]:

            row.append(
                InlineKeyboardButton(
                    name,
                    callback_data=f"news_game_{key}",
                )
            )

        keyboard.append(row)

    keyboard.append(
        [
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="global_cancel",
            )
        ]
    )

    await update.message.reply_text(
        "📰 Новости игр\n\n"
        "Выбери игру:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================================================
# ПОИСК НОВОСТЕЙ
# =========================================================

async def search_news(
    query,
    context,
    telegram_message,
):

    await telegram_message.edit_text(
        "📰 Ищу свежие новости...\n\n"
        "Подожди несколько секунд."
    )

    try:

        prompt = (
            "Найди самые свежие и действительно "
            "существенные новости по игре:\n"
            f"{query}\n\n"

            "Используй Google Search.\n"
            "Ориентируйся на актуальные публикации "
            "и официальные источники, если они доступны.\n\n"

            "Выбери до 5 интересных новостей.\n\n"

            "Для каждой новости напиши:\n"
            "1. Короткий заголовок\n"
            "2. Что произошло — 1-2 предложения\n"
            "3. Источник и URL\n\n"

            "Не придумывай новости и ссылки.\n"
            "Если свежих важных новостей мало — "
            "покажи только найденные."
        )

        result = await gemini_request(
            prompt,
            use_search=True,
        )

        context.user_data[
            "news_result"
        ] = result

        context.user_data[
            "mode"
        ] = "news_results"

        keyboard = [
            [
                InlineKeyboardButton(
                    "🤖 Выбрать новость",
                    callback_data="news_select",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Искать снова",
                    callback_data="news_search_again",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Закрыть",
                    callback_data="global_cancel",
                )
            ],
        ]

        await telegram_message.edit_text(
            "📰 Свежие новости:\n\n"
            f"{result}",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception:

        logger.exception(
            "News search error"
        )

        await telegram_message.edit_text(
            "❌ Не удалось получить новости.\n\n"
            "Попробуй ещё раз."
        )


# =========================================================
# AI ПО НОВОСТИ
# =========================================================

async def create_post_from_news(
    update,
    context,
    news_text,
):

    query = update.callback_query

    await query.edit_message_text(
        "🤖 Делаю пост из новости..."
    )

    style_key = context.user_data.get(
        "news_style",
        "f1cklock",
    )

    style = STYLES.get(
        style_key,
        STYLES["f1cklock"],
    )

    prompt = (
        "Ты ведёшь Telegram-канал стримера F1cklock.\n\n"

        f"Используй стиль:\n"
        f"{style['prompt']}\n\n"

        "На основе новости ниже создай "
        "готовый Telegram-пост на русском языке.\n\n"

        "Сохрани фактический смысл новости.\n"
        "Не придумывай детали.\n"
        "Не пиши длинную статью.\n"
        "Не говори, что ты AI.\n"
        "Не используй заглушки для ссылок.\n\n"

        "Сделай пост интересным для игровой аудитории.\n\n"

        "НОВОСТЬ:\n"
        f"{news_text}"
    )

    try:

        text = await gemini_request(
            prompt
        )

        context.user_data[
            "ai_text"
        ] = text

        context.user_data[
            "ai_prompt"
        ] = (
            "Создать пост из этой новости:\n"
            + news_text
        )

        context.user_data[
            "ai_photo"
        ] = None

        context.user_data[
            "ai_style"
        ] = style_key

        context.user_data[
            "mode"
        ] = "ai"

        await query.edit_message_text(
            "📰 Готовый пост:\n\n"
            f"{text}\n\n"
            f"🎨 Стиль: {style['name']}",
            reply_markup=ai_keyboard(),
        )

    except Exception:

        logger.exception(
            "News AI error"
        )

        await query.edit_message_text(
            "❌ Не удалось сделать пост."
        )


# =========================================================
# AI КНОПКИ
# =========================================================

async def ai_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query.from_user.id != OWNER_ID:

        await query.answer()

        return

    await query.answer()

    # -----------------------------------------
    # ДОБАВИТЬ ФОТО
    # -----------------------------------------

    if query.data == "ai_add_photo":

        context.user_data[
            "mode"
        ] = "ai_photo"

        await query.message.reply_text(
            "🖼️ Пришли фотографию.\n\n"
            "Я добавлю её к этому AI-посту.",
            reply_markup=CANCEL_MENU,
        )

        return

    # -----------------------------------------
    # СМЕНИТЬ СТИЛЬ
    # -----------------------------------------

    if query.data == "ai_change_style":

        context.user_data[
            "mode"
        ] = "ai_choose_style_change"

        await query.message.reply_text(
            "🎨 Выбери новый стиль:",
            reply_markup=styles_keyboard(
                prefix="change_style"
            ),
        )

        return

    # -----------------------------------------
    # ИЗМЕНИТЬ
    # -----------------------------------------

    if query.data == "ai_edit":

        context.user_data[
            "mode"
        ] = "ai_edit"

        await query.message.reply_text(
            "✏️ Напиши, что изменить.\n\n"
            "Например:\n"
            "«Сделай короче»\n"
            "«Добавь юмора»\n"
            "«Сделай более дерзким»",
            reply_markup=CANCEL_MENU,
        )

        return

    # -----------------------------------------
    # ОТМЕНА
    # -----------------------------------------

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

    # -----------------------------------------
    # ОПУБЛИКОВАТЬ
    # -----------------------------------------

    if query.data == "ai_publish":

        text = context.user_data.get(
            "ai_text"
        )

        photo_id = context.user_data.get(
            "ai_photo"
        )

        if not text:

            await query.edit_message_text(
                "❌ Текст больше недоступен."
            )

            return

        text = fix_twitch_link(
            text
        )

        try:

            if photo_id:

                if len(text) <= 1024:

                    await context.bot.send_photo(
                        chat_id=CHANNEL,
                        photo=photo_id,
                        caption=text,
                    )

                else:

                    await context.bot.send_photo(
                        chat_id=CHANNEL,
                        photo=photo_id,
                    )

                    await context.bot.send_message(
                        chat_id=CHANNEL,
                        text=text,
                    )

            else:

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

            logger.exception(
                "AI publish error"
            )

            await query.edit_message_text(
                "❌ Не удалось опубликовать пост.\n\n"
                "Проверь права бота в канале."
            )

        return

    # -----------------------------------------
    # ПЕРЕДЕЛАТЬ
    # -----------------------------------------

    if query.data == "ai_retry":

        prompt = context.user_data.get(
            "ai_prompt"
        )

        if not prompt:

            await query.edit_message_text(
                "❌ Исходная тема больше недоступна."
            )

            return

        await query.edit_message_text(
            "🔄 Переделываю..."
        )

        style_key = context.user_data.get(
            "ai_style",
            "f1cklock",
        )

        style = STYLES.get(
            style_key,
            STYLES["f1cklock"],
        )

        try:

            ai_prompt = (
                "Создай другой вариант "
                "Telegram-поста на русском языке.\n\n"

                f"Стиль:\n{style['prompt']}\n\n"

                "Пост должен быть живым, коротким "
                "и естественным.\n"

                "Не придумывай факты.\n"
                "Не используй заглушки ссылок.\n\n"

                f"Тема:\n{prompt}"
            )

            text = await gemini_request(
                ai_prompt
            )

            context.user_data[
                "ai_text"
            ] = text

            await query.edit_message_text(
                "🤖 Новый вариант:\n\n"
                f"{text}\n\n"
                f"🎨 Стиль: {style['name']}",
                reply_markup=ai_keyboard(),
            )

        except Exception:

            logger.exception(
                "AI retry error"
            )

            await query.edit_message_text(
                "❌ Gemini снова не ответил.\n"
                "Попробуй ещё раз."
            )

        return


# =========================================================
# ОБРАБОТКА CALLBACK СТИЛЕЙ
# =========================================================

async def style_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query.from_user.id != OWNER_ID:

        await query.answer()

        return

    await query.answer()

    data = query.data

    # -----------------------------------------
    # НОВЫЙ AI-ПОСТ
    # -----------------------------------------

    if data.startswith(
        "style_"
    ):

        style_key = data[
            len("style_"):
        ]

        if style_key not in STYLES:
            return

        context.user_data[
            "ai_style"
        ] = style_key

        context.user_data[
            "mode"
        ] = "ai"

        style = STYLES[
            style_key
        ]

        await query.edit_message_text(
            f"🎨 Выбран стиль: {style['name']}\n\n"
            "Теперь напиши тему поста."
        )

        await query.message.reply_text(
            "🤖 Напиши тему поста:",
            reply_markup=CANCEL_MENU,
        )

        return

    # -----------------------------------------
    # СМЕНА СТИЛЯ
    # -----------------------------------------

    if data.startswith(
        "change_style_"
    ):

        style_key = data[
            len("change_style_"):
        ]

        if style_key not in STYLES:
            return

        context.user_data[
            "ai_style"
        ] = style_key

        prompt = context.user_data.get(
            "ai_prompt"
        )

        if not prompt:
            return

        style = STYLES[
            style_key
        ]

        await query.edit_message_text(
            "🎨 Меняю стиль..."
        )

        try:

            ai_prompt = (
                "Переделай этот Telegram-пост "
                "в новый стиль.\n\n"

                f"Новый стиль:\n"
                f"{style['prompt']}\n\n"

                "Сохрани факты и смысл.\n"
                "Не добавляй выдуманные факты.\n"
                "Дай только готовый текст поста.\n\n"

                f"Исходный пост:\n"
                f"{context.user_data.get('ai_text', '')}"
            )

            text = await gemini_request(
                ai_prompt
            )

            context.user_data[
                "ai_text"
            ] = text

            photo_id = context.user_data.get(
                "ai_photo"
            )

            keyboard = (
                ai_photo_keyboard()
                if photo_id
                else ai_keyboard()
            )

            await query.edit_message_text(
                "🤖 Новый стиль:\n\n"
                f"{text}\n\n"
                f"🎨 {style['name']}",
                reply_markup=keyboard,
            )

        except Exception:

            logger.exception(
                "Style change error"
            )

            await query.edit_message_text(
                "❌ Не удалось сменить стиль."
            )


# =========================================================
# НОВОСТНЫЕ CALLBACK
# =========================================================

async def news_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query.from_user.id != OWNER_ID:

        await query.answer()

        return

    await query.answer()

    data = query.data

    # -----------------------------------------
    # ВЫБОР ИГРЫ
    # -----------------------------------------

    if data.startswith(
        "news_game_"
    ):

        game_key = data[
            len("news_game_"):
        ]

        game_name = NEWS_GAMES.get(
            game_key
        )

        if not game_name:
            return

        context.user_data[
            "news_game"
        ] = game_name

        await search_news(
            game_name,
            context,
            query.message,
        )

        return

    # -----------------------------------------
    # ИСКАТЬ СНОВА
    # -----------------------------------------

    if data == "news_search_again":

        game_name = context.user_data.get(
            "news_game"
        )

        if game_name:

            await search_news(
                game_name,
                context,
                query.message,
            )

        return

    # -----------------------------------------
    # ВЫБОР НОВОСТИ
    # -----------------------------------------

    if data == "news_select":

        news_text = context.user_data.get(
            "news_result"
        )

        if not news_text:
            return

        context.user_data[
            "mode"
        ] = "news_choose_style"

        context.user_data[
            "selected_news"
        ] = news_text

        await query.message.reply_text(
            "🎨 Выбери стиль для новости:",
            reply_markup=styles_keyboard(
                prefix="news_style"
            ),
        )

        return

    # -----------------------------------------
    # СТИЛЬ НОВОСТИ
    # -----------------------------------------

    if data.startswith(
        "news_style_"
    ):

        style_key = data[
            len("news_style_"):
        ]

        if style_key not in STYLES:
            return

        context.user_data[
            "news_style"
        ] = style_key

        news_text = context.user_data.get(
            "selected_news"
        )

        if not news_text:
            return

        style = STYLES[
            style_key
        ]

        await query.edit_message_text(
            "🤖 Делаю пост..."
        )

        prompt = (
            "Ты ведёшь Telegram-канал "
            "стримера F1cklock.\n\n"

            f"Стиль:\n{style['prompt']}\n\n"

            "На основе найденных новостей "
            "создай короткий готовый пост "
            "для Telegram.\n\n"

            "Выбери наиболее интересный факт "
            "из представленного материала.\n"

            "Не придумывай факты.\n"
            "Не говори, что ты AI.\n"
            "Не делай длинную статью.\n\n"

            f"Новости:\n{news_text}"
        )

        try:

            text = await gemini_request(
                prompt
            )

            context.user_data[
                "ai_text"
            ] = text

            context.user_data[
                "ai_prompt"
            ] = news_text

            context.user_data[
                "ai_photo"
            ] = None

            context.user_data[
                "ai_style"
            ] = style_key

            context.user_data[
                "mode"
            ] = "ai"

            await query.edit_message_text(
                "📰 Готовый пост:\n\n"
                f"{text}\n\n"
                f"🎨 {style['name']}",
                reply_markup=ai_keyboard(),
            )

        except Exception:

            logger.exception(
                "News style AI error"
            )

            await query.edit_message_text(
                "❌ Не удалось создать пост."
            )


# =========================================================
# ОБЩАЯ ОТМЕНА
# =========================================================

async def global_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query.from_user.id != OWNER_ID:
        await query.answer()
        return

    await query.answer()

    context.user_data.clear()

    await query.edit_message_text(
        "❌ Отменено."
    )

    await query.message.reply_text(
        "Главное меню:",
        reply_markup=MAIN_MENU,
    )


# =========================================================
# ОБРАБОТКА СООБЩЕНИЙ
# =========================================================

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

    # =====================================================
    # ОТМЕНА
    # =====================================================

    if text == "❌ Отмена":

        context.user_data.clear()

        await message.reply_text(
            "❌ Отменено.",
            reply_markup=MAIN_MENU,
        )

        return

    # =====================================================
    # ДОБАВЛЕНИЕ ФОТО К AI
    # =====================================================

    if (
        context.user_data.get("mode")
        == "ai_photo"
    ):

        if message.photo:

            photo_id = (
                message.photo[-1].file_id
            )

            context.user_data[
                "ai_photo"
            ] = photo_id

            context.user_data[
                "mode"
            ] = "ai"

            ai_text = context.user_data.get(
                "ai_text",
                "",
            )

            ai_text = fix_twitch_link(
                ai_text
            )

            # Telegram ограничивает caption
            # у фото 1024 символами.
            if len(ai_text) <= 950:

                await message.reply_photo(
                    photo=photo_id,
                    caption=(
                        "🖼️ Фото добавлено!\n\n"
                        + ai_text
                    ),
                    reply_markup=ai_photo_keyboard(),
                )

            else:

                await message.reply_photo(
                    photo=photo_id,
                    reply_markup=ai_photo_keyboard(),
                )

                await message.reply_text(
                    "📝 Текст поста:\n\n"
                    + ai_text
                )

            return

        await message.reply_text(
            "🖼️ Нужно отправить именно фотографию.",
            reply_markup=CANCEL_MENU,
        )

        return

    # =====================================================
    # РЕДАКТИРОВАНИЕ AI
    # =====================================================

    if (
        context.user_data.get("mode")
        == "ai_edit"
    ):

        if not message.text:
            await message.reply_text(
                "✏️ Напиши текстом, что изменить."
            )
            return

        instruction = message.text

        old_text = context.user_data.get(
            "ai_text",
            "",
        )

        style_key = context.user_data.get(
            "ai_style",
            "f1cklock",
        )

        style = STYLES.get(
            style_key,
            STYLES["f1cklock"],
        )

        waiting = await message.reply_text(
            "✏️ Переделываю..."
        )

        try:

            prompt = (
                "Отредактируй Telegram-пост.\n\n"

                f"Стиль:\n{style['prompt']}\n\n"

                f"Что нужно изменить:\n"
                f"{instruction}\n\n"

                "Сохрани важные факты.\n"
                "Не добавляй выдуманные факты.\n"
                "Дай только готовый пост.\n\n"

                f"Исходный текст:\n"
                f"{old_text}"
            )

            new_text = await gemini_request(
                prompt
            )

            context.user_data[
                "ai_text"
            ] = new_text

            context.user_data[
                "mode"
            ] = "ai"

            photo_id = context.user_data.get(
                "ai_photo"
            )

            keyboard = (
                ai_photo_keyboard()
                if photo_id
                else ai_keyboard()
            )

            await waiting.edit_text(
                "✏️ Готово!\n\n"
                f"{new_text}",
                reply_markup=keyboard,
            )

        except Exception:

            logger.exception(
                "AI edit error"
            )

            await waiting.edit_text(
                "❌ Не удалось изменить текст."
            )

        return

    # =====================================================
    # ГЛАВНОЕ МЕНЮ
    # =====================================================

    if text == "🎮 Создать пост":

        await create_post(
            update,
            context,
        )

        return

    if text == "🔴 Анонс стрима":

        await stream_announce(
            update,
            context,
        )

        return

    if text == "📡 Я в эфире":

        await live_stream(
            update,
            context,
        )

        return

    if text == "📅 Расписание":

        await schedule_menu(
            update,
            context,
        )

        return

    if text == "🎬 Клип":

        await create_clip(
            update,
            context,
        )

        return

    if text == "📰 Новости игр":

        await news_start(
            update,
            context,
        )

        return

    if text == "🤖 Создать с ИИ":

        await ai_start(
            update,
            context,
        )

        return

    if text == "⚙️ Настройки":

        await settings(
            update,
            context,
        )

        return

    if text == "⬅️ Главное меню":

        context.user_data.clear()

        await message.reply_text(
            "Главное меню:",
            reply_markup=MAIN_MENU,
        )

        return

    if text == "➕ Добавить стрим":

        await add_stream(
            update,
            context,
        )

        return

    if text == "📋 Показать расписание":

        await show_schedule(
            update,
            context,
        )

        return

    # =====================================================
    # AI — ОЖИДАЕМ ТЕМУ
    # =====================================================

    if (
        context.user_data.get("mode")
        == "ai"
    ):

        if message.text:

            await generate_ai_post(
                update,
                context,
                message.text,
            )

        return

    # =====================================================
    # РАСПИСАНИЕ
    # =====================================================

    if (
        context.user_data.get("mode")
        == "schedule"
    ):

        step = context.user_data.get(
            "step"
        )

        if step == "date":

            context.user_data[
                "date"
            ] = text

            context.user_data[
                "step"
            ] = "game"

            await message.reply_text(
                "🎮 Теперь напиши название игры.",
                reply_markup=CANCEL_MENU,
            )

            return

        if step == "game":

            date = context.user_data.get(
                "date"
            )

            schedule = (
                context.bot_data.setdefault(
                    "schedule",
                    [],
                )
            )

            schedule.append(
                {
                    "date": date,
                    "game": text,
                }
            )

            context.user_data.clear()

            await message.reply_text(
                "✅ Стрим добавлен "
                "в расписание.",
                reply_markup=MAIN_MENU,
            )

            return

    # =====================================================
    # АНОНС / ЭФИР
    # =====================================================

    mode = context.user_data.get(
        "mode"
    )

    step = context.user_data.get(
        "step"
    )

    if mode in (
        "announce",
        "live",
    ):

        if step == "game":

            context.user_data[
                "game"
            ] = text

            context.user_data[
                "step"
            ] = "content"

            await message.reply_text(
                "📝 Теперь пришли текст, "
                "фото или видео для поста.",
                reply_markup=CANCEL_MENU,
            )

            return

        if step == "content":

            await publish_media(
                update,
                context,
            )

            context.user_data.clear()

            await message.reply_text(
                "✅ Опубликовано в канале.",
                reply_markup=MAIN_MENU,
            )

            return

    # =====================================================
    # ОБЫЧНЫЙ ПОСТ / КЛИП
    # =====================================================

    if mode in (
        "post",
        "clip",
    ):

        await publish_media(
            update,
            context,
        )

        context.user_data.clear()

        await message.reply_text(
            "✅ Опубликовано в канале.",
            reply_markup=MAIN_MENU,
        )

        return


# =========================================================
# АВТООБЪЯВЛЕНИЕ РАСПИСАНИЯ
# =========================================================

async def schedule_checker(
    context: ContextTypes.DEFAULT_TYPE,
):

    schedule = context.bot_data.get(
        "schedule",
        [],
    )

    if not schedule:
        return

    now = datetime.now().strftime(
        "%d.%m %H:%M"
    )

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

                schedule.remove(
                    item
                )

            except Exception:

                logger.exception(
                    "Schedule announcement error"
                )


# =========================================================
# ЗАПУСК
# =========================================================

def main():

    if not BOT_TOKEN:

        raise RuntimeError(
            "BOT_TOKEN не задан"
        )

    if not WEBHOOK_URL:

        raise RuntimeError(
            "WEBHOOK_URL не задан"
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # AI
    application.add_handler(
        CallbackQueryHandler(
            ai_buttons,
            pattern=r"^ai_"
        )
    )

    # Стили
    application.add_handler(
        CallbackQueryHandler(
            style_callback,
            pattern=r"^(style_|change_style_)"
        )
    )

    # Новости
    application.add_handler(
        CallbackQueryHandler(
            news_callback,
            pattern=r"^news_"
        )
    )

    # Общая отмена
    application.add_handler(
        CallbackQueryHandler(
            global_cancel,
            pattern=r"^global_cancel$"
        )
    )

    # Все сообщения
    application.add_handler(
        MessageHandler(
            filters.ALL
            & ~filters.COMMAND,
            handle_message,
        )
    )

    # Проверка расписания
    application.job_queue.run_repeating(
        schedule_checker,
        interval=60,
        first=10,
    )

    logger.info(
        "Bot starting..."
    )

    application.run_webhook(
        listen="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "10000",
            )
        ),
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
