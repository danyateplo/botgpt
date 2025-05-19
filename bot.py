import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- Настройки ---

TELEGRAM_TOKEN = '7253845822:AAGltWcYaaXVvr4Pb95pP6lXh8lYfZInoI4'
GEMINI_API_KEY = 'AIzaSyA6xHo-SD3jRybAiQt7CHxWgIpWWZrllhw'
GEMINI_API_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'
ADMIN_ID = 1543197217  # ID администратора для уведомлений
STABLE_DIFFUSION_URL = "https://stablediffusionapi.com/api/v3/text2img"  # пример бесплатного API (замени, если надо)
STABLE_DIFFUSION_API_KEY = "fVXd0fX5bbKI5UihmUBFBGb2cqYFbfyK8djYn7xY11cDovQRQ891MjISNm5x"

# --- Функция генерации текста через Gemini ---
def generate_gemini_text(prompt: str) -> str:
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"Ошибка при запросе Gemini: {e}"

# --- Функция генерации изображения через Stable Diffusion ---
def generate_image(prompt: str) -> str | None:
    payload = {
        "key": STABLE_DIFFUSION_API_KEY,
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, bad anatomy",
        "width": "512",
        "height": "512",
        "samples": "1",
        "num_inference_steps": "30",
        "seed": None,
        "guidance_scale": 7.5,
    }
    try:
        resp = requests.post(STABLE_DIFFUSION_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            return data["output"][0]
        else:
            return None
    except Exception:
        return None

# --- Обработчики команд и сообщений ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Уведомить админа, если новый пользователь
    await update.message.reply_text(
        "Привет! Я бот с нейросетью Gemini 2.0 и генерацией картинок.\n"
        "Напиши любой текст, чтобы получить ответ или /img <текст> для картинки.\n\n"
        "Доступные команды:\n"
        "/start - старт\n"
        "/history - история запросов\n"
        "/set_ad <текст> - установить рекламу (только для админа)\n"
        "/img <текст> - сгенерировать картинку"
    )
    if context.application.bot_data.get("users") is None:
        context.application.bot_data["users"] = set()
    if user.id not in context.application.bot_data["users"]:
        context.application.bot_data["users"].add(user.id)
        await context.bot.send_message(ADMIN_ID, f"Новый пользователь: {user.full_name} (id={user.id})")

async def set_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("У тебя нет прав использовать эту команду.")
        return
    ad_text = ' '.join(context.args)
    context.application.bot_data['ad'] = ad_text
    await update.message.reply_text("Реклама установлена!")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = context.user_data.get("history", [])
    if not hist:
        await update.message.reply_text("История пуста.")
        return
    reply = "<b>Твоя история (последние 5):</b>\n"
    for i, pair in enumerate(hist[-5:], 1):
        reply += f"\n<b>{i}. Вопрос:</b> {pair['вопрос']}\n<b>Ответ:</b> {pair['ответ']}\n"
    await update.message.reply_text(reply, parse_mode='HTML')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat = update.message.chat

    await chat.send_action(action="typing")

    loading_msg = await update.message.reply_text("Генерирую ответ...")

    answer = generate_gemini_text(user_text)

    ad = context.application.bot_data.get("ad", "<i>Здесь могла быть ваша реклама</i>")
    final_text = f"💡 <b>Ответ Gemini:</b>\n\n{answer}\n\n—\n{ad}"

    if "history" not in context.user_data:
        context.user_data["history"] = []
    context.user_data["history"].append({"вопрос": user_text, "ответ": answer})

    await loading_msg.edit_text(final_text, parse_mode='HTML')

async def generate_img(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Напиши /img <текст>, чтобы сгенерировать картинку.")
        return
    prompt = ' '.join(context.args)

    await update.message.chat.send_action("upload_photo")
    loading_msg = await update.message.reply_text("Генерирую картинку... Это может занять несколько секунд.")

    image_url = generate_image(prompt)
    if image_url:
        await loading_msg.delete()
        await update.message.reply_photo(photo=image_url, caption=f"Вот твоя картинка по запросу: {prompt}")
    else:
        await loading_msg.edit_text("⚠️ Ошибка при генерации изображения. Попробуй позже.")

# --- Запуск бота ---

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('set_ad', set_ad))
    app.add_handler(CommandHandler('history', history))
    app.add_handler(CommandHandler('img', generate_img))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
