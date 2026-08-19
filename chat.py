import logging
import os
import time
import json
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
ADMIN_ID = os.getenv("ADMIN_ID") # আপনার টেলিগ্রাম আইডি এখানে দিন (রেলওয়ে ভেরিয়েবল থেকে নিবে)

CHAT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# মেমোরি এবং নলেজ স্টোরেজ
user_history = {} # ইউজারের চ্যাট হিস্ট্রি রাখার জন্য
developer_knowledge = "আমি একজন প্রফেশনাল অ্যাপ এবং ওয়েবসাইট ডেভেলপার অ্যাসিস্ট্যান্ট।" # ডিফল্ট তথ্য

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = InferenceClient(token=HF_API_TOKEN)

# --- নলেজ ম্যানেজমেন্ট (Admin Only) ---
def update_knowledge(new_info):
    global developer_knowledge
    developer_knowledge = new_info
    # আপনি চাইলে এখানে ফাইল সেভ করার কোড যোগ করতে পারেন

def query_jarvis_ai(user_id, prompt):
    global user_history, developer_knowledge
    
    # সিস্টেম ইনস্ট্রাকশন (বটকে আপনার অ্যাসিস্ট্যান্ট হিসেবে তৈরি করা)
    system_instruction = f"""
    You are a professional assistant for a Web & App Developer. 
    Developer's Info & Services: {developer_knowledge}
    Always respond professionally. If the user asks for code, provide full code. 
    If a response is cut off, and user says 'Continue', provide the remaining part of the previous code.
    Respond in the language the user is using (Bengali/English/Hindi).
    """

    # হিস্ট্রি ম্যানেজমেন্ট (সর্বশেষ ৫টি মেসেজ মনে রাখবে)
    if user_id not in user_history:
        user_history[user_id] = []
    
    messages = [{"role": "system", "content": system_instruction}]
    for msg in user_history[user_id][-6:]: # সর্বশেষ ৩ জোড়া মেসেজ
        messages.append(msg)
    
    messages.append({"role": "user", "content": prompt})

    for attempt in range(3):
        try:
            response = client.chat_completion(
                model=CHAT_MODEL,
                messages=messages,
                max_tokens=1500, # বড় উত্তরের জন্য টোকেন বাড়ানো হয়েছে
                temperature=0.7
            )
            ai_reply = response.choices[0].message.content
            
            # হিস্ট্রিতে সেভ করা
            user_history[user_id].append({"role": "user", "content": prompt})
            user_history[user_id].append({"role": "assistant", "content": ai_reply})
            
            return ai_reply
            
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(5)
                
    return "😊 Sir, I am facing a temporary issue. Please try again."

# --- টেলিগ্রাম হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😊 Hello! I am your Developer Assistant. How can I help you today?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    
    # ১. এডমিন কমান্ড চেক (অ্যাসিস্ট্যান্টকে শেখানোর জন্য)
    if user_id == ADMIN_ID and user_text.startswith("/update"):
        new_info = user_text.replace("/update", "").strip()
        update_knowledge(new_info)
        await update.message.reply_text("✅ Assistant Knowledge Updated successfully, Sir!")
        return

    # ২. জেনারেল চ্যাট
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # টাইম চেক
    if any(k in user_text.lower() for k in ["time", "সময়", "baje"]):
        await update.message.reply_text(f"😊 It's {datetime.now().strftime('%I:%M %p')}")
        return

    response = query_jarvis_ai(user_id, user_text)
    
    # বড় মেসেজ হলে টেলিগ্রামের লিমিট অনুযায়ী পাঠানো
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            await update.message.reply_text(response[i:i+4000])
    else:
        await update.message.reply_text(response)

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("AI Assistant is Online...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
