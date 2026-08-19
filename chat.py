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

# স্টেবল মডেল
CHAT_MODEL = "HuggingFaceH4/zephyr-7b-beta"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# অফিশিয়াল ক্লায়েন্ট সেটআপ
try:
    client = InferenceClient(model=CHAT_MODEL, token=HF_API_TOKEN)
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
        return "😊 Sir, JARVIS Brain is not initialized. Check your API Token."
    
    lang = detect_language(prompt)
    sys_msg = "You are JARVIS. Respond in Bengali. Short 1 sentence." if lang == "bn" else \
              "You are JARVIS. Respond in Hindi. Short 1 sentence." if lang == "hi" else \
              "You are JARVIS. Respond in English. Be very concise."

    full_prompt = f"<|system|>\n{sys_msg}</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"

    for attempt in range(3):
        try:
            # অফিশিয়াল মেথড ব্যবহার করে কল করা
            response = client.text_generation(full_prompt, max_new_tokens=80, stop_sequences=["</s>"])
            return f"😊 {response.strip()}"
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            if "503" in str(e): # মডেল লোড হচ্ছে
                time.sleep(10)
            else:
                time.sleep(3)
                
    return "😊 I'm having a temporary network hiccup. Please try again in a moment."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😊 JARVIS System Online. Ready for your commands, Sir!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text: return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # টাইম চেক
    if any(k in user_text.lower() for k in ["time", "সময়", "समय", "baje"]):
        await update.message.reply_text(f"😊 Sir, it's {datetime.now().strftime('%I:%M %p')}")
        return

    response = query_jarvis_ai(user_text)
    await update.message.reply_text(response)

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing!")
        return
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("JARVIS is active...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
