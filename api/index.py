import os
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
BOT_TOKEN = os.environ.get('BOT_TOKEN')
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA=" 
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
    # Initial Message: 10%
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
            
            # Update to 70%
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
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ Bot Active! Send a link."})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_and_animate(chat_id, mid, urls[0]))
            loop.close()

    return "ok", 200

@app.route('/')
def home():
    return "Progress Bar Bot is Online!"

# Vercel requirement
app = app
