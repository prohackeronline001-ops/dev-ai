import logging
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# .env ফাইল লোড করা
load_dotenv()

# --- কনফিগারেশন (Railway Variables থেকে নিবে) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# ✅ সুপার স্টেবল মডেল (এটি ব্যবহারের জন্য কোনো বাড়তি পারমিশন লাগে না)
CHAT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
# ইনফোরেন্স API এর জন্য স্ট্যান্ডার্ড এন্ডপয়েন্ট
CHAT_API_URL = f"https://api-inference.huggingface.co/models/{CHAT_MODEL}"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ভাষা শনাক্তকরণ ---
def detect_language(text: str) -> str:
    bengali_chars = ['া', 'ি', 'ী', 'ু', 'ূ', 'ৃ', 'ে', 'ৈ', 'ো', 'ৌ', 'ং', 'ঃ', 'ঁ']
    hindi_chars = ['ा', 'ি', 'ী', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः']
    bengali_count = sum(1 for char in text if char in bengali_chars)
    hindi_count = sum(1 for char in text if char in hindi_chars)
    if bengali_count > hindi_count: return "bn"
    elif hindi_count > 0: return "hi"
    else: return "en"

def get_system_prompt(lang: str) -> str:
    if lang == "bn":
        return 'You are JARVIS. Respond in Bengali. Short 1 sentence.'
    elif lang == "hi":
        return 'You are JARVIS. Respond in Hindi. Short 1 sentence.'
    else:
        return 'You are JARVIS. Respond in English. Short 1 sentence.'

# --- AI কুয়েরি ফাংশন ---
def query_jarvis_ai(prompt: str) -> str:
    lang = detect_language(prompt)
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    # ফ্রি টায়ারের জন্য পেইলড ফরম্যাট সহজ করা হলো
    payload = {
        "inputs": f"<|im_start|>system\n{get_system_prompt(lang)}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
        "parameters": {"max_new_tokens": 100, "return_full_text": False}
    }
    
    for attempt in range(3):
        try:
            response = requests.post(CHAT_API_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 503: # মডেল লোড হচ্ছে
                logger.info("Model loading... waiting 10s")
                time.sleep(10)
                continue
                
            response.raise_for_status()
            result = response.json()
            
            # রেজাল্ট থেকে টেক্সট বের করা
            if isinstance(result, list):
                ai_message = result[0].get('generated_text', "")
            else:
                ai_message = result.get('generated_text', "")
            
            if ai_message:
                return f"😊 {ai_message.strip()}"
                
        except Exception as e:
            logger.error(f"Attempt {attempt+1} Error: {e}")
            time.sleep(3)
            
    return "😊 Sorry sir, I'm having trouble connecting to my brain. Please check your API token."

# --- টেলিগ্রাম হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😊 JARVIS System Online. How can I help you, Sir?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # টাইম চেক
    if any(k in user_text.lower() for k in ["time", "সময়", "समय", "baje"]):
        now = datetime.now().strftime("%I:%M %p")
        await update.message.reply_text(f"😊 Sir, it's {now}")
        return

    response = query_jarvis_ai(user_text)
    await update.message.reply_text(response)

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing!")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("JARVIS is starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()