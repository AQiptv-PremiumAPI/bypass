from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import requests
import re

app = Flask(__name__)

# --- CONFIGURATION ---
API_ID = 39707299 
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
BOT_TOKEN = '8231200837:AAEsVzdlOy5YIgcNxl8OC_F8jPEkDKD8oi8'
STRING_SESSION = "1BVtsOIMBu48IMdzGoRhEdl0HjgsTLB7l2ycOVhheWk4lG1AWZ7e7kJYe3xPeBDmVjVRedINYfPznkkA9U0CWgJPcrcO-JhRE-HfnCmmu9siQMhOPwgEvlSrrTiabVQJv3vfPLl_fFQgwOZeoT_GwiQ_7ym-mBhu80BVGEmmffbVJTG9XQuQiYOtPPRDNG-TCBECcQQhzirS8bkmuSkWX1x74Szs_mOTkDUiSUE_NQpRyNmUTMKcowPHY7R9eE6Zj6eSGjCZAHHOspphfugneuBy9SHX-EYRNUpZDmZoFP5C6zsNZ7sptXA_LHCh34cZD-d5de0buN9mMkg4xZRkw4_cGBpJemwI=" 
TARGET_BOT = "@nick_bypass_bot"

def bot_request(method, payload):
    return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload)

def get_progress_bar(percent):
    # 10 boxes total: har box 10% represent karta hai
    done = int(percent / 10)
    remain = 10 - done
    bar = "■" * done + "□" * remain
    return f"[{bar}] {percent}%"

async def get_and_animate(chat_id, message_id, user_msg_url):
    # Initial Message: 20%
    resp = bot_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"⏳ **Processing...**\n`{get_progress_bar(10)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    
    processing_msg_id = resp.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=45) as conv:
            await conv.send_message(user_msg_url)
            
            # Update to 40%
            if processing_msg_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": processing_msg_id,
                    "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
                })

            await conv.get_response() # Skip first msg
            
            # Update to 80%
            if processing_msg_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": processing_msg_id,
                    "text": f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"
                })

            try:
                response = await conv.get_response(timeout=15)
                raw_text = response.text
            except:
                raw_text = "❌ Error: Timeout"

            # Parsing Links
            all_urls = re.findall(r'https?://[^\s]+', raw_text)
            if len(all_urls) >= 2:
                # 100% Update just before showing result
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": processing_msg_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                
                final_text = (
                    f"**ORIGINAL LINK:**\n{all_urls[0]}\n\n"
                    f"**BYPASSED LINK:**\n{all_urls[1]}"
                )
            else:
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@sandibypassbot")

            # Final Result
            if processing_msg_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": processing_msg_id,
                    "text": final_text, "parse_mode": "Markdown", "disable_web_page_preview": True
                })
                
    except Exception as e:
        if processing_msg_id:
            bot_request("editMessageText", {
                "chat_id": chat_id, "message_id": processing_msg_id, "text": f"⚠️ Error: {str(e)}"
            })
    finally:
        await client.disconnect()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg["text"]
        mid = msg["message_id"]

        if text.startswith("/start"):
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ Join @Riotv_Bypass to bypass ads url."})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_and_animate(chat_id, mid, urls[0]))

    return "ok", 200

@app.route('/')
def home():
    return "Progress Bar Bot is Online!"
