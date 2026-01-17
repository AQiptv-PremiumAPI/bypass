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

# Sabse powerful URL cleaner
def extract_clean_urls(text):
    # Ye regex sirf 'http' se shuru hone wali strings nikalega aur kachra saaf karega
    raw_urls = re.findall(r'https?://[^\s]+', text)
    cleaned = []
    for url in raw_urls:
        # Aage peeche ke symbols (┖, │, etc.) ko filter karna
        clean = re.sub(r'^[┖│─╰╯\s]+|[┖│─╰╯\s]+$', '', url)
        if clean:
            cleaned.append(clean)
    return cleaned

async def get_and_animate(chat_id, message_id, user_msg_url):
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
            
            if p_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
                })

            await conv.get_response() # Skip Nick's processing message
            
            if p_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Bypassing...**\n`{get_progress_bar(80)}`", "parse_mode": "Markdown"
                })

            response = await conv.get_response(timeout=35)
            raw_text = response.text

            # --- UNIVERSAL EXTRACTION ---
            found_links = extract_clean_urls(raw_text)

            if len(found_links) >= 2:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                
                final_text = (
                    "✅ **BYPASSED!**\n\n"
                    f"**ORIGINAL LINK:**\n{found_links[0]}\n\n"
                    f"**BYPASSED LINK:**\n{found_links[1]}"
                )
            else:
                # Agar regex fail ho, toh fallback
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@sandibypassbot")

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

        # Primary check to see if it's a URL
        if "http" in text:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_and_animate(chat_id, mid, text.strip()))
            loop.close()

    return "ok", 200

@app.route('/')
def home():
    return "Universal Fix Live!"
