import os
import requests
import logging
import asyncio

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# 🔐 КЛЮЧИ И НАСТРОЙКИ
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or '7253845822:AAGltWcYaaXVvr4Pb95pP6lXh8lYfZInoI4'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or 'AIzaSyA6xHo-SD3jRybAiQt7CHxWgIpWWZrllhw'
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN") or 'r8_HIB3ha4Vfn7v21xSimfapnYVt5QoAsP3REp0l'
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
ADMIN_ID = 1543197217  # 👈 Укажи свой Telegram user ID

logging.basicConfig(level=logging.INFO)

# 📜 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, <b>{user.first_name}</b>!\n"
        f"Я бот на базе Google Gemini 🤖\n"
        f"Напиши вопрос — и я отвечу!\n\n"
        f"💡 Команды:\n"
        f"/img <описание> — сгенерировать картинку\n"
        f"/history — последние запросы\n/help — помощь",
        parse_mode="HTML"
    )

    # 🔔 Админу уведомление
    if user.id != ADMIN_ID:
        text = f"👤 Новый пользователь:\nID: <code>{user.id}</code>\nИмя: {user.full_name}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode="HTML")

# 📜 Команда /help
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Доступные команды:\n"
        "/start — начало\n"
        "/img <описание> — генерация изображения\n"
        "/history — история сообщений\n"
        "/set_ad <текст> — установить рекламу (только для админа)",
        parse_mode="HTML"
    )

# 🧾 Команда /set_ad
async def set_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 У тебя нет прав.")
    ad_text = ' '.join(context.args)
    context.application.bot_data['ad'] = f"<i>{ad_text}</i>"
    await update.message.reply_text("✅ Реклама обновлена!")

# 🕘 История
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = context.user_data.get("history", [])
    if not hist:
        return await update.message.reply_text("📭 История пуста.")
    text = "<b>🕘 Твоя история:</b>\n"
    for i, pair in enumerate(hist[-5:], 1):
        text += f"\n<b>{i}. Вопрос:</b> {pair['вопрос']}\n<b>Ответ:</b> {pair['ответ']}\n"
    await update.message.reply_text(text, parse_mode='HTML')

# 🧠 Gemini текстовая генерация
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat = update.message.chat
    await chat.send_action(action="typing")
    loading_msg = await update.message.reply_text("⏳ Думаю...")

    payload = {"contents": [{"parts": [{"text": user_text}]}]}
    headers = {"Content-Type": "application/json"}
    try:
        r = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        answer = f"⚠️ Ошибка при запросе: {e}"

    # 💬 Реклама
    ad = context.application.bot_data.get("ad", "<i>🤝 Сотрудничество? Напиши админу!</i>")
    final = f"💡 <b>Ответ Gemini:</b>\n\n{answer}\n\n—\n{ad}"

    # 💾 История
    context.user_data.setdefault("history", []).append({
        "вопрос": user_text, "ответ": answer
    })
    await loading_msg.edit_text(final, parse_mode="HTML")

# 🎨 Генерация изображения
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("📸 Используй: /img <описание>")

    prompt = ' '.join(context.args)
    await update.message.reply_text("🎨 Генерирую изображение...")

    try:
        # Запрос на генерацию
        url = "https://api.replicate.com/v1/predictions"
        headers = {
            "Authorization": f"Token {REPLICATE_API_TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "version": "c508bf47b6f97ec2c7db06670188b54c46e55a679fa2f0c27e30dfbde67478b0",
            "input": {"prompt": prompt}
        }
        r = requests.post(url, headers=headers, json=data)
        r.raise_for_status()
        prediction = r.json()
        status_url = prediction["urls"]["get"]

        # Ожидание результата
        while True:
            res = requests.get(status_url, headers=headers).json()
            if res["status"] == "succeeded":
                image_url = res["output"][0]
                break
            elif res["status"] == "failed":
                raise Exception("Генерация не удалась.")
            await asyncio.sleep(1)

        await update.message.reply_photo(photo=image_url, caption="✨ Вот твоё изображение!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка при генерации изображения: {e}")

# ▶️ Запуск
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('set_ad', set_ad))
    app.add_handler(CommandHandler('history', history))
    app.add_handler(CommandHandler('img', generate_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # ⚙️ Кнопки автоподсказки
    await app.bot.set_my_commands([
        BotCommand("start", "Запуск бота"),
        BotCommand("img", "Создать изображение по описанию"),
        BotCommand("history", "История запросов"),
        BotCommand("set_ad", "Установить рекламу"),
        BotCommand("help", "Помощь"),
    ])

    print("✅ Бот запущен!")
    await app.run_polling()

# 🚀 Запуск
if __name__ == '__main__':
    asyncio.run(main())
