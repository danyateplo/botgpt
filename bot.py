
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)


# --- Конфиги ---
TELEGRAM_TOKEN = '7253845822:AAGltWcYaaXVvr4Pb95pP6lXh8lYfZInoI4'
GEMINI_API_KEY = 'AIzaSyA6xHo-SD3jRybAiQt7CHxWgIpWWZrllhw'
GEMINI_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
ADMIN_ID = 1543197217  # ID администратора для уведомлений
STABLE_DIFFUSION_API = "https://stablediffusionapi.com/api/v3/text2img"  # пример бесплатного API (замени, если надо)
STABLE_DIFFUSION_API_KEY = "fVXd0fX5bbKI5UihmUBFBGb2cqYFbfyK8djYn7xY11cDovQRQ891MjISNm5x"

# --- Утилиты ---

async def notify_admin_about_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name
    # Проверяем, был ли пользователь уже
    known_users = context.application.bot_data.setdefault("known_users", set())
    if user_id not in known_users:
        known_users.add(user_id)
        msg = f"👤 Новый пользователь: <b>{user_name}</b> (ID: {user_id})"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='HTML')

# --- Текстовый функционал ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await notify_admin_about_new_user(update, context)

    keyboard = [
        [InlineKeyboardButton("/history", callback_data='history')],
        [InlineKeyboardButton("/set_ad", callback_data='set_ad')],
        [InlineKeyboardButton("/img", callback_data='img')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Привет! Я бот с нейросетью <b>Gemini 2.0</b> от Google.\n"
        "📩 Просто отправь мне вопрос, и я отвечу!\n\n"
        "Используй кнопки ниже для команд:",
        parse_mode='HTML',
        reply_markup=reply_markup,
    )


async def set_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У тебя нет прав использовать эту команду.")
        return
    ad_text = ' '.join(context.args)
    if not ad_text:
        await update.message.reply_text("Использование: /set_ad <текст рекламы>")
        return
    context.application.bot_data['ad'] = ad_text
    await update.message.reply_text("✅ Реклама установлена!")


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = context.user_data.get("history", [])
    if not hist:
        await update.message.reply_text("📭 История пуста.")
        return
    reply = "<b>🕘 Твоя история (последние 5 запросов):</b>\n"
    for i, pair in enumerate(hist[-5:], 1):
        reply += f"\n<b>{i}. Вопрос:</b> {pair['вопрос']}\n<b>Ответ:</b> {pair['ответ']}\n"
    await update.message.reply_text(reply, parse_mode='HTML')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat = update.message.chat

    # Пишем статус "печатает..."
    await chat.send_action(ChatAction.TYPING)

    # Отправляем сообщение о загрузке
    loading_msg = await update.message.reply_text("⌛ Генерирую ответ...")

    # Запрос к Gemini API
    payload = {
        "contents": [
            {"parts": [{"text": user_text}]}
        ]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        answer = f"⚠️ Ошибка при запросе: {e}"

    # Реклама курсивом
    ad = context.application.bot_data.get("ad", "<i>Здесь могла быть ваша реклама 😊</i>")
    final_text = f"💡 <b>Ответ Gemini:</b>\n\n{answer}\n\n—\n{ad}"

    # Сохраняем историю
    if "history" not in context.user_data:
        context.user_data["history"] = []
    context.user_data["history"].append({"вопрос": user_text, "ответ": answer})

    # Обновляем сообщение
    await loading_msg.edit_text(final_text, parse_mode='HTML')


# --- Генерация изображений ---

async def generate_image(prompt: str) -> str:
    # Здесь пример запроса к бесплатному API stable diffusion (можешь заменить)
    try:
        payload = {
            "key": STABLE_DIFFUSION_API_KEY,
            "prompt": prompt,
            "negative_prompt": "blurry, lowres, bad anatomy",
            "width": 512,
            "height": 512,
            "samples": 1,
            "num_inference_steps": 20,
            "seed": None,
        }
        response = requests.post(STABLE_DIFFUSION_API, json=payload)
        response.raise_for_status()
        data = response.json()
        # Возвращаем URL первого изображения
        return data["output"][0]
    except Exception as e:
        return f"Ошибка при генерации изображения: {e}"


async def img_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("❗ Использование: /img <текст для изображения>")
        return
    prompt = ' '.join(args)
    await update.message.reply_text("🎨 Генерирую изображение, подожди...")

    url_or_error = await generate_image(prompt)
    if url_or_error.startswith("Ошибка"):
        await update.message.reply_text(url_or_error)
    else:
        await update.message.reply_photo(photo=url_or_error, caption=f"🖼️ Результат для: {prompt}")


# --- Обработка inline кнопок (пример) ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "history":
        hist = context.user_data.get("history", [])
        if not hist:
            await query.edit_message_text("📭 История пуста.")
            return
        reply = "<b>🕘 Ваша история (последние 5 запросов):</b>\n"
        for i, pair in enumerate(hist[-5:], 1):
            reply += f"\n<b>{i}. Вопрос:</b> {pair['вопрос']}\n<b>Ответ:</b> {pair['ответ']}\n"
        await query.edit_message_text(reply, parse_mode='HTML')
    elif data == "set_ad":
        await query.edit_message_text("Используйте команду /set_ad <текст рекламы> для установки рекламы (только для админа).")
    elif data == "img":
        await query.edit_message_text("Используйте команду /img <текст для генерации изображения>.")


# --- Запуск бота ---

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_ad", set_ad))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("img", img_command))

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен...")
    await app.run_polling()


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(main())
        else:
            loop.run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())
