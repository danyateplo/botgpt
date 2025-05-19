import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# ==== Настройки ====
TELEGRAM_TOKEN = '7253845822:AAGltWcYaaXVvr4Pb95pP6lXh8lYfZInoI4'
GEMINI_API_KEY = 'AIzaSyA6xHo-SD3jRybAiQt7CHxWgIpWWZrllhw'
GEMINI_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
ADMIN_ID = 1543197217  # Замени на свой Telegram ID

# ==== Команды ====

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\nЯ бот с нейросетью <b>Gemini 2.0</b> от Google.\nПросто задай мне вопрос.",
        parse_mode='HTML'
    )
    # Уведомим админа о новом пользователе
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"👤 Новый пользователь: {user.first_name} (@{user.username}) | ID: {user.id}")

# /set_ad
async def set_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 У тебя нет прав использовать эту команду.")
        return
    ad_text = ' '.join(context.args)
    context.application.bot_data['ad'] = f"<i>{ad_text}</i>"
    await update.message.reply_text("✅ Реклама установлена!")

# ==== Обработка текстов ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat = update.message.chat

    await chat.send_action(action="typing")
    loading_msg = await update.message.reply_text("⌛️ Генерирую ответ...")

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
        answer = f"Ошибка при запросе: {e}"

    ad = context.application.bot_data.get("ad", "<i>Здесь могла быть ваша реклама</i>")
    final_text = f"💡 <b>Ответ Gemini:</b>\n\n{answer}\n\n—\n{ad}"

    context.user_data.setdefault("history", []).append({"вопрос": user_text, "ответ": answer})
    await loading_msg.edit_text(final_text, parse_mode='HTML')

# ==== Запуск ====
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('set_ad', set_ad))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен...")
    app.run_polling()



