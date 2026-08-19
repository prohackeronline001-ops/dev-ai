import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

# --- CONFIG ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# সবচাইতে নির্ভরযোগ্য মডেল
CHAT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ক্লায়েন্ট সেটআপ
try:
    client = InferenceClient(token=HF_API_TOKEN)
except Exception as e:
    logger.error(f"Client Init Error: {e}")
    client = None

def detect_language(text: str) -> str:
    bn = ['া', 'ি', 'ী', 'ু', 'ূ', 'ে', 'ৈ', 'ো', 'ৌ']
    hi = ['ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ']
    bn_c = sum(1 for c in text if c in bn)
    hi_c = sum(1 for c in text if c in hi)
    return "bn" if bn_c > hi_c else ("hi" if hi_c > 0 else "en")

def query_jarvis_ai(prompt: str) -> str:
    if not client:
        return "😊 Sir, JARVIS brain is offline. Check API settings."
    
    lang = detect_language(prompt)
    sys_msg = "You are JARVIS. Respond in Bengali. Short 1 sentence." if lang == "bn" else \
              "You are JARVIS. Respond in Hindi. Short 1 sentence." if lang == "hi" else \
              "You are JARVIS. Respond in English. Be concise."

    # চ্যাট ফরম্যাটে মেসেজ সাজানো (এটি conversational এরর দূর করবে)
    messages = [
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": prompt}
    ]

    for attempt in range(3):
        try:
            # চ্যাট কমপ্লিশন মেথড ব্যবহার (সবচেয়ে স্টেবল)
            response = client.chat_completion(
                model=CHAT_MODEL,
                messages=messages,
                max_tokens=100,
                temperature=0.7
            )
            reply = response.choices[0].message.content
            return f"😊 {reply.strip()}"
            
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            if "503" in str(e) or "loading" in str(e).lower():
                time.sleep(10) # মডেল লোড হওয়ার সময় দেওয়া
            else:
                time.sleep(3)
                
    return "😊 I am having a bit of trouble focusing. Could you try again, Sir?"

# --- টেলিগ্রাম হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😊 JARVIS System Online. Ready to assist you, Sir!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # টাইম চেক
    if any(k in user_text.lower() for k in ["time", "সময়", "সময়", "baje"]):
        now = datetime.now().strftime("%I:%M %p")
        await update.message.reply_text(f"😊 Sir, it's currently {now}")
        return

    # AI রেসপন্স
    response = query_jarvis_ai(user_text)
    await update.message.reply_text(response)

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing!")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("JARVIS is starting (Chat Mode)...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
