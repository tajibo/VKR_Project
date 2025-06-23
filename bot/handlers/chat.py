# bot/handlers/chat.py
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from telegram import Update
from telegram.ext import ContextTypes
from bot.handlers.utils import log_activity

model: AutoModelForCausalLM = None
tokenizer: AutoTokenizer = None
device: torch.device = None

@log_activity("chat")
async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global model, tokenizer, device
    if not model or not tokenizer or not device:
        await update.message.reply_text("Модель ещё не загружена, попробуйте позже.")
        return

    user_text = update.message.text.strip()
    prompt = f"<User>: {user_text}\n<Bot>:"
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256)
    input_ids = inputs.input_ids.to(device)
    attention_mask = inputs.attention_mask.to(device)

    output_ids = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=128,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=False,
        num_beams=1,
    )
    decoded = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    bot_answer = decoded.split("<Bot>:")[-1].strip()
    await update.message.reply_text(bot_answer)
