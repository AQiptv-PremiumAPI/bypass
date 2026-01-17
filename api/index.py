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
BOT_TOKEN = '8420015561:AAFdkmCe8uVGbB9FJWhV4emj9s_xFvwMViQ'
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA=" 
TARGET_BOT = "@nick_bypass_bot"

def bot_request(method, payload):
    return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload)

async def get_raw_response(chat_id, message_id, user_msg_url):
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=60) as conv:
            # Nick Bot ko message bhejo
            await conv.send_message(user_msg_url)
            
            # Nick Bot ke processing messages skip karo
            # Ye tab tak wait karega jab tak final result na mil jaye
            while True:
                response = await conv.get_response(timeout=45)
                # Agar message mein "Bypassed Link" word hai, toh ye final response hai
                if "Bypassed Link" in response.text or "https://" in response.text:
                    raw_text = response.text
                    break
            
            # Nick Bot ka username badal kar apna lagao
            final_text = raw_text.replace("@Nick_Bypass_Bot", "@RioBypassBot")

            # Bilkul waisa hi message bhej do (No modification)
            bot_request("sendMessage", {
                "chat_id": chat_id,
                "text": final_text,
                "reply_to_message_id": message_id,
                "disable_web_page_preview": True
            })
                
    except Exception as e:
        # Error aane par hi kuch extra print hoga
        pass
    finally:
        await client.disconnect()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id, text, mid = msg["chat"]["id"], msg["text"], msg["message_id"]

        if text.startswith("/start"):
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ Send Link to Bypass."})
            return "ok", 200

        # Agar link hai toh process karo
        if "http" in text:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_raw_response(chat_id, mid, text.strip()))
            loop.close()

    return "ok", 200

@app.route('/')
def home():
    return "Raw Forwarder is Online!"
