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
# ADMIN_ID অবশ্যই স্ট্রিং হিসেবে চেক হবে
ADMIN_ID = os.getenv("ADMIN_ID") 

CHAT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# মেমোরি এবং নলেজ স্টোরেজ (গ্লোবাল ভেরিয়েবল)
user_history = {}
# ডিফল্ট নলেজ সেট করে রাখা হলো
developer_knowledge = "আমি একজন প্রফেশনাল অ্যাপ এবং ওয়েবসাইট ডেভেলপার অ্যাসিস্ট্যান্ট।"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = InferenceClient(token=HF_API_TOKEN)

# --- AI কুয়েরি ফাংশন ---
def query_jarvis_ai(user_id, prompt):
    global user_history, developer_knowledge
    
    system_instruction = f"""
    You are a professional assistant for a Web & App Developer. 
    Developer's Info: {developer_knowledge}
    Rules:
    1. Respond professionally.
    2. Provide FULL CODE when asked. Do not skip parts.
    3. If user says 'Continue', look at your previous response and provide the remaining part.
    4. Language: Match the user's language (Bengali/English/Hindi).
    """

    if user_id not in user_history:
        user_history[user_id] = []
    
    messages = [{"role": "system", "content": system_instruction}]
    # মেমোরি লিমিট (শেষ ১০টি মেসেজ মনে রাখবে)
    for msg in user_history[user_id][-10:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat_completion(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=2000, # আরও বড় উত্তরের জন্য বাড়ানো হলো
            temperature=0.7
        )
        ai_reply = response.choices[0].message.content
        
        # মেমোরিতে সেভ করা
        user_history[user_id].append({"role": "user", "content": prompt})
        user_history[user_id].append({"role": "assistant", "content": ai_reply})
        
        return ai_reply
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "😊 Sir, my connection is a bit slow. Could you please repeat that?"

# --- টেলিগ্রাম হ্যান্ডলারস ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😊 Hello! I am your Developer Assistant. How can I help you, Sir?")

async def update_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global developer_knowledge
    user_id = str(update.effective_user.id)
    
    # এডমিন চেক (নিশ্চিত করে নিন ADMIN_ID রেলওয়েতে সেট করা আছে)
    if user_id == ADMIN_ID:
        if context.args:
            developer_knowledge = " ".join(context.args)
            await update.message.reply_text("✅ Knowledge base updated successfully, Sir!")
        else:
            await update.message.reply_text("❌ Please provide some info. Example: /update I am a dev.")
    else:
        await update.message.reply_text("⛔ Sorry, only the Admin can update my settings.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_text = update.message.text
    if not user_text: return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # AI রেসপন্স
    response = query_jarvis_ai(user_id, user_text)
    
    # টেলিগ্রামের ৪০০০ ক্যারেক্টার লিমিট হ্যান্ডেল করা
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            await update.message.reply_text(response[i:i+4000])
    else:
        await update.message.reply_text(response)

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing!")
        return
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # কমান্ড হ্যান্ডলার
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("update", update_info))
    
    # মেসেজ হ্যান্ডলার (কমান্ড বাদে সব টেক্সট মেসেজ)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Developer Assistant is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
