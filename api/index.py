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
    remain = 10 - done
    bar = "■" * done + "□" * remain
    return f"[{bar}] {percent}%"

def clean_url(url):
    # Link ke aage peeche se symbols (┖, │, ─) aur extra kachra saaf karne ke liye
    return re.sub(r'^[┖│─╰╯\s]+|[┖│─╰╯\s]+$', '', url)

async def get_and_animate(chat_id, message_id, user_msg_url):
    # Initial: 20%
    resp = bot_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"⏳ **Processing...**\n`{get_progress_bar(20)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    
    p_id = resp.get("result", {}).get("message_id")
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=60) as conv:
            await conv.send_message(user_msg_url)
            
            # Update: 40%
            if p_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
                })

            await conv.get_response() # Nick Processing Msg
            
            # Update: 80%
            if p_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Bypassing...**\n`{get_progress_bar(80)}`", "parse_mode": "Markdown"
                })

            response = await conv.get_response(timeout=30)
            raw_text = response.text

            # 🔥 Sabse Solid Regex: Link ke beech ka kachra filter karke pure link uthayega
            found_links = re.findall(r'https?://[^\s┖│─╰╯]+', raw_text)

            if len(found_links) >= 2:
                # Clean the links (Symbols hatane ke liye)
                orig_link = clean_url(found_links[0])
                bypass_link = clean_url(found_links[1])

                # Update: 100%
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                
                final_text = (
                    "✅ **BYPASSED!**\n\n"
                    f"**ORIGINAL LINK:**\n{orig_link}\n\n"
                    f"**BYPASSED LINK:**\n{bypass_link}"
                )
            else:
                # Agar regex fail ho toh purana text hi forward kardo
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@sandibypassbot")

            # Result edit
            if p_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": final_text, "parse_mode": "Markdown", "disable_web_page_preview": True
                })
                
    except Exception as e:
        if p_id:
            bot_request("editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id, text, mid = msg["chat"]["id"], msg["text"], msg["message_id"]

        if text.startswith("/start"):
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ Bot Active! Send any link."})
            return "ok", 200

        # Link check
        urls = re.findall(r'https?://[^\s┖│─╰╯]+', text)
        if urls:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_and_animate(chat_id, mid, urls[0]))
            loop.close()

    return "ok", 200

@app.route('/')
def home():
    return "Universal Bypass Bot is Online!"
