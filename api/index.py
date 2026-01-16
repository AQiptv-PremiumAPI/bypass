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

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def get_and_animate(chat_id, message_id, user_msg_url):
    # FAST START: Ek hi baar 50% par message bhej dena
    resp = bot_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"⏳ **Processing...**\n`{get_progress_bar(50)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    
    processing_msg_id = resp.get("result", {}).get("message_id")
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    
    try:
        await client.start()
        async with client.conversation(TARGET_BOT, timeout=30) as conv:
            await conv.send_message(user_msg_url)
            
            # Seedha response ka wait (Animation edits kam karne se speed badhti hai)
            await conv.get_response() # Skip Processing msg
            response = await conv.get_response() # Link msg
            raw_text = response.text

            all_urls = re.findall(r'https?://[^\s]+', raw_text)
            if len(all_urls) >= 2:
                final_text = (
                    "✅ **BYPASSED!**\n\n"
                    f"**ORIGINAL LINK:**\n{all_urls[0]}\n\n"
                    f"**BYPASSED LINK:**\n{all_urls[1]}"
                )
            else:
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@sandibypassbot")

            # Final response update seedha (No extra middle steps)
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
        chat_id, text, mid = msg["chat"]["id"], msg["text"], msg["message_id"]

        if text.startswith("/start"):
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ Bot Superfast Active!"})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            # Threading ya background task ki tarah run karna speed ke liye zaroori hai
            asyncio.run(get_and_animate(chat_id, mid, urls[0]))

    return "ok", 200

@app.route('/')
def home():
    return "Superfast Bot is Running!"
