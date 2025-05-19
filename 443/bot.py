import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# Настройки
TELEGRAM_TOKEN = '8140231133AAHua40lJeqAiGiTlUMTDDsIAukm4iueggE'
GEMINI_API_KEY = 'AIzaSyA6xHo-SD3jRybAiQt7CHxWgIpWWZrllhw'
GEMINI_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
ADMIN_ID = 1543197217  # ← замени на свой Telegram user ID

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот с нейросетью <b>Gemini 2.0</b> от Google.\n"
        "Просто задай мне вопрос — и получишь ответ!",
        parse_mode='HTML'
    )

# Команда /set_ad
async def set_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У тебя нет прав использовать эту команду.")
        return
    ad_text = ' '.join(context.args)
    context.application.bot_data['ad'] = ad_text
    await update.message.reply_text("Реклама установлена!")

# Команда /history
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = context.user_data.get("history", [])
    if not hist:
        await update.message.reply_text("История пуста.")
        return
    reply = "<b>Твоя история:</b>\n"
    for i, pair in enumerate(hist[-5:], 1):
        reply += f"\n<b>{i}. Вопрос:</b> {pair['вопрос']}\n<b>Ответ:</b> {pair['ответ']}\n"
    await update.message.reply_text(reply, parse_mode='HTML')

# Обработка обычных сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat = update.message.chat

    # Статус "печатает..."
    await chat.send_action(action="typing")

    # Уведомление о генерации
    loading_msg = await update.message.reply_text("Генерирую ответ...")

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling()
