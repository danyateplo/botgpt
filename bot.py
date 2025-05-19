import requests
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackContext,
)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\nЯ бот с нейросетью <b>Gemini 2.0</b> от Google.\nПросто задай мне вопрос или используй /img для генерации изображений!",
        parse_mode='HTML'
    )
    if user.id != ADMIN_ID:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🆕 Новый пользователь: {user.full_name} (@{user.username})")

# Команда /set_ad
async def set_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 У тебя нет прав использовать эту команду.")
        return
    ad_text = ' '.join(context.args)
    context.application.bot_data['ad'] = f"<i>{ad_text}</i>"
    await update.message.reply_text("✅ Реклама установлена!")

# Команда /history
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = context.user_data.get("history", [])
    if not hist:
        await update.message.reply_text("📭 История пуста.")
        return
    reply = "🕘 <b>Твоя история:</b>\n"
    for i, pair in enumerate(hist[-5:], 1):
        reply += f"\n<b>{i}. Вопрос:</b> {pair['вопрос']}\n<b>Ответ:</b> {pair['ответ']}\n"
    await update.message.reply_text(reply, parse_mode='HTML')

# Команда /img
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🖼️ Использование: /img <описание изображения>")
        return

    prompt = ' '.join(context.args)
    await update.message.reply_text("🎨 Генерирую изображение...")

    try:
        response = requests.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "version": "db21e45d3f7df31c13e7c2ee9080da54bf17b0a09e59dadd7d300d83e6de65e7",
                "input": {"prompt": prompt}
            }
        )
        prediction = response.json()
        image_url = prediction['output'][0] if 'output' in prediction else None

        if image_url:
            await update.message.reply_photo(photo=image_url, caption=f"🖼️ Результат по запросу: {prompt}")
        else:
            await update.message.reply_text("❌ Не удалось сгенерировать изображение.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при генерации изображения: {e}")

# Обработка обычных сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat = update.message.chat

    # Статус "печатает..."
    await chat.send_action(action="typing")

    # Уведомление о генерации
    loading_msg = await update.message.reply_text("⌛ Генерирую ответ...")

    # Запрос к Gemini API
    payload = {
        "contents": [
            {
                "parts": [{"text": user_text}]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        answer = f"Ошибка при запросе: {e}"

    # Реклама курсивом
    ad = context.application.bot_data.get("ad", "<i>Здесь могла быть ваша реклама</i>")
    final_text = f"💡 <b>Ответ Gemini:</b>\n\n{answer}\n\n—\n{ad}"

    # История
    if "history" not in context.user_data:
        context.user_data["history"] = []
    context.user_data["history"].append({"вопрос": user_text, "ответ": answer})

    # Обновить сообщение
    await loading_msg.edit_text(final_text, parse_mode='HTML')

# Запуск приложения
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('set_ad', set_ad))
    app.add_handler(CommandHandler('history', history))
    app.add_handler(CommandHandler('img', generate_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Бот запущен...")
    app.run_polling()
