import requests
import replicate
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

# ==== Настройки ====
TELEGRAM_TOKEN = '7253845822:AAGltWcYaaXVvr4Pb95pP6lXh8lYfZInoI4'
GEMINI_API_KEY = 'AIzaSyA6xHo-SD3jRybAiQt7CHxWgIpWWZrllhw'
GEMINI_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
REPLICATE_API_TOKEN = 'r8_HIB3ha4Vfn7v21xSimfapnYVt5QoAsP3REp0l'
ADMIN_ID = 1543197217  # Замени на свой Telegram ID

# Создаём клиент replicate один раз
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# ==== Команды ====

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\nЯ бот с нейросетью <b>Gemini 2.0</b> от Google.\nПросто задай мне вопрос или используй /img для генерации картинки!",
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

# /history
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = context.user_data.get("history", [])
    if not hist:
        await update.message.reply_text("🕳 История пуста.")
        return
    reply = "<b>🕘 История:</b>\n"
    for i, pair in enumerate(hist[-5:], 1):
        reply += f"\n<b>{i}. Вопрос:</b> {pair['вопрос']}\n<b>Ответ:</b> {pair['ответ']}\n"
    await update.message.reply_text(reply, parse_mode='HTML')

# /img — генерация изображения
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗️Напиши запрос после команды /img\nПример: /img кот в очках")
        return
    prompt = ' '.join(context.args)
    await update.message.reply_text("🎨 Генерирую изображение... ⏳")
    try:
        model = replicate_client.models.get("stability-ai/stable-diffusion")
        version = model.versions.get("db21e45b8b37ac0515c8edc535780047c9f00a7eb2f04619b1a1c2f72b75e39c")
        output = version.predict(prompt=prompt)
        if output and isinstance(output, list):
            await update.message.reply_photo(photo=output[0], caption=f"🖼 <b>Запрос:</b> <i>{prompt}</i>", parse_mode='HTML')
        else:
            await update.message.reply_text("⚠️ Не удалось сгенерировать изображение.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка генерации изображения: {e}")

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
    app.add_handler(CommandHandler('history', history))
    app.add_handler(CommandHandler('img', generate_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот запущен...")
    app.run_polling()
