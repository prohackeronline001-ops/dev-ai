import logging
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# ✅ আরও স্টেবল মডেল যা সব সময় ফ্রি-তে কাজ করে
CHAT_MODEL = "HuggingFaceH4/zephyr-7b-beta"
CHAT_API_URL = f"https://api-inference.huggingface.co/models/{CHAT_MODEL}"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_language(text: str) -> str:
    bengali_chars = ['া', 'ি', 'ী', 'ু', 'ূ', 'ৃ', 'ে', 'ৈ', 'ো', 'ৌ', 'ং', 'ঃ', 'ঁ']
    hindi_chars = ['া', 'ি', 'ী', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः']
    bengali_count = sum(1 for char in text if char in bengali_chars)
    hindi_count = sum(1 for char in text if char in hindi_chars)
    return "bn" if bengali_count > hindi_count else ("hi" if hindi_count > 0 else "en")

def get_system_prompt(lang: str) -> str:
    if lang == "bn": return 'You are JARVIS. Respond in Bengali. Short 1 sentence.'
    if lang == "hi": return 'You are JARVIS. Respond in Hindi. Short 1 sentence.'
    return 'You are JARVIS. Respond in English. Short 1 sentence.'

def query_jarvis_ai(prompt: str) -> str:
    if not HF_API_TOKEN or not HF_API_TOKEN.startswith("hf_"):
        return "😊 Sir, your HF API Token seems invalid. Please check Railway variables."

    lang = detect_language(prompt)
    headers = {"Authorization": f"Bearer {HF_API_TOKEN.strip()}"}
    
    # Zephyr মডেলের জন্য স্ট্যান্ডার্ড প্রম্পট ফরম্যাট
    formatted_prompt = f"<|system|>\n{get_system_prompt(lang)}</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
    payload = {"inputs": formatted_prompt, "parameters": {"max_new_tokens": 80}}
    
    for attempt in range(3):
        try:
            response = requests.post(CHAT_API_URL, headers=headers, json=payload, timeout=25)
            
            if response.status_code == 200:
                result = response.json()
                # টেক্সট ক্লিন করা
                if isinstance(result, list) and len(result) > 0:
                    text = result[0].get('generated_text', "")
                    # শুধু অ্যাসিস্ট্যান্টের উত্তরটুকু নেওয়া
                    ai_reply = text.split("<|assistant|>")[-1].strip()
                    return f"😊 {ai_reply}"
            
            elif response.status_code == 503: # মডেল লোড হচ্ছে
                logger.warning("Model is loading... waiting 8s")
                time.sleep(8)
                continue
            else:
                logger.error(f"HF Error {response.status_code}: {response.text}")
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Network Error: {e}")
            time.sleep(2)
            
    return "😊 I'm still having trouble. Check Railway Logs for 'HF Error'."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😊 JARVIS System Online. Use a Classic Read Token if this fails.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    response = query_jarvis_ai(user_text)
    await update.message.reply_text(response)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
