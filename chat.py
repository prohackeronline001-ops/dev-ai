import logging
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# .env ফাইল লোড করা (লোকাল টেস্টিং এর জন্য)
load_dotenv()

# --- কনফিগারেশন (Railway Variables থেকে নিবে) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# স্টেবল AI মডেল (Llama 3.2 3B ফ্রি টায়ারের জন্য সেরা)
CHAT_MODEL = "meta-llama/Llama-3.2-3B-Instruct"
CHAT_API_URL = f"https://api-inference.huggingface.co/models/{CHAT_MODEL}/v1/chat/completions"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ভাষা শনাক্তকরণ ---
def detect_language(text: str) -> str:
    bengali_chars = ['া', 'ি', 'ী', 'ু', 'ূ', 'ৃ', 'ে', 'ৈ', 'ো', 'ৌ', 'ং', 'ঃ', 'ঁ']
    hindi_chars = ['ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः']
    bengali_count = sum(1 for char in text if char in bengali_chars)
    hindi_count = sum(1 for char in text if char in hindi_chars)
    if bengali_count > hindi_count: return "bn"
    elif hindi_count > 0: return "hi"
    else: return "en"

def get_system_prompt(lang: str) -> str:
    if lang == "bn":
        return 'You are JARVIS. Respond in Bengali. Use feminine grammar (আমি সাহায্য করছি). Keep it 1-2 short sentences.'
    elif lang == "hi":
        return 'You are JARVIS. Respond in Hindi. Use feminine grammar (मैं कर सकती हूँ). Keep it 1-2 short sentences.'
    else:
        return 'You are JARVIS. Respond in English. Be concise and professional.'

# --- AI কুয়েরি ফাংশন (Error Proof) ---
def query_jarvis_ai(prompt: str) -> str:
    lang = detect_language(prompt)
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        'model': CHAT_MODEL,
        'messages': [
            {'role': 'system', 'content': get_system_prompt(lang)},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 150,
        'temperature': 0.7
    }
    
    for attempt in range(3):
        try:
            response = requests.post(CHAT_API_URL, headers=headers, json=payload, timeout=30)
            
            # যদি মডেল লোড হতে থাকে (ফ্রি সার্ভারে এটা হয়)
            if response.status_code == 503:
                time.sleep(10)
                continue
                
            response.raise_for_status()
            result = response.json()
            ai_message = result.get('choices', [{}])[0].get('message', {}).get('content', "")
            
            if ai_message:
                return f"😊 {ai_message.strip()}"
                
        except Exception as e:
            logger.error(f"Attempt {attempt+1} error: {e}")
            time.sleep(3)
            
    if lang == "bn": return "😊 ক্ষমা করবেন স্যার, আমার সার্ভারে সমস্যা হচ্ছে।"
    if lang == "hi": return "😊 माफ़ कीजिये सर, सर्वर में समस्या है।"
    return "😊 Sorry sir, I'm having trouble connecting to my brain right now."

# --- টেলিগ্রাম হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😊 JARVIS Online. How can I help you, Sir?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # টাইপিং এনিমেশন দেখাবে
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # লোকাল টাইম চেক (সার্ভারের জন্য নিরাপদ)
    if any(k in user_text.lower() for k in ["time", "সময়", "समय", "baje"]):
        now = datetime.now().strftime("%I:%M %p")
        await update.message.reply_text(f"😊 Sir, it's {now}")
        return

    # AI এর কাছে পাঠানো
    response = query_jarvis_ai(user_text)
    await update.message.reply_text(response)

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN missing!")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("JARVIS is running...")
    # drop_pending_updates=True দিলে পুরাতন মেসেজগুলো কনফ্লিক্ট করবে না
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
