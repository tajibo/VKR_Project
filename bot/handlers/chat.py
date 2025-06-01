# bot/handlers/chat.py

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.utils import log_activity

# Эти глобальные переменные будут проинициализированы из main.py
model: AutoModelForCausalLM = None
tokenizer: AutoTokenizer = None
device: torch.device = None

@log_activity("chat")
async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает любое текстовое сообщение (не команду).
    Использует дообученную модель ruDialoGPT, загруженную из Hugging Face Hub.
    """
    user_text = update.message.text.strip()
    # Формируем промпт в том же формате, что при обучении:
    prompt = f"<User>: {user_text}\n<Bot>:"

    # Токенизируем, усечём до 256 токенов (если слишком длинно)
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=256,
    )
    input_ids = inputs["input_ids"].to(device)
    attention_mask = inputs["attention_mask"].to(device)

    # Генерируем ответ
    output_ids = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=128,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False,
        num_beams=1,
    )

    decoded = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    # Обрезаем всё до (и включая) "<Bot>:" и берём только ответ
    if "<Bot>:" in decoded:
        bot_answer = decoded.split("<Bot>:")[-1].strip()
    else:
        bot_answer = decoded.strip()

    await update.message.reply_text(bot_answer)
