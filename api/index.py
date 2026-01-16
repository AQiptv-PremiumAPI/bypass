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
ALLOWED_CHAT = "riotv_bypass"

def bot_request(method, payload):
    return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=10)

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def get_and_animate(chat_id, message_id, user_msg_url):
    resp = bot_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"⏳ **Processing...**\n`{get_progress_bar(20)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    
    p_id = resp.get("result", {}).get("message_id")
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

    try:
        await client.start()
        async with client.conversation(TARGET_BOT, timeout=30) as conv:
            await conv.send_message(user_msg_url)
            if p_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Bypassing...**\n`{get_progress_bar(60)}`", "parse_mode": "Markdown"
                })
            await conv.get_response()
            response = await conv.get_response()
            raw_text = response.text
            all_urls = re.findall(r'https?://[^\s]+', raw_text)
            if len(all_urls) >= 2:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                final_text = f"✅ **BYPASSED!**\n\n**ORIGINAL:**\n{all_urls[0]}\n\n**BYPASSED:**\n{all_urls[1]}"
            else:
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@sandibypassbot")
            if p_id:
                bot_request("editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": final_text, "parse_mode": "Markdown", "disable_web_page_preview": True})
    except Exception as e:
        if p_id: bot_request("editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return "ok", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    chat_type = msg["chat"]["type"] # 'private', 'group', or 'supergroup'
    text = msg.get("text", "")
    mid = msg["message_id"]
    chat_username = msg["chat"].get("username", "").lower()

    # --- 1. SABSE PEHLE DM CHECK (Sabse Majboot Filter) ---
    if chat_type == "private":
        bot_request("sendMessage", {
            "chat_id": chat_id,
            "text": "❌ **Access Denied!**\n\nJoin @riotv_bypass to use this bot.\nI don't work in Private DMs.",
            "parse_mode": "Markdown"
        })
        return "ok", 200

    # --- 2. AB GROUP KA LOGIC ---
    if ALLOWED_CHAT.lower() in chat_username or chat_username == ALLOWED_CHAT.lower():
        if text.startswith("/start"):
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ **Bot is Active!**\nSend any link to bypass."})
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
    return "Bot is Live"
