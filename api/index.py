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

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def process_bypass(chat_id, message_id, user_msg_url):
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    
    # 1. Sabse pehle Processing message bhej do
    resp = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": chat_id,
        "text": f"⏳ **Processing...**\n`{get_progress_bar(20)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    
    p_id = resp.get("result", {}).get("message_id")

    try:
        await client.start()
        async with client.conversation(TARGET_BOT, timeout=30) as conv:
            # 2. Nick Bot ko message bhejo turant
            await conv.send_message(user_msg_url)
            
            if p_id:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⚡ **Extracting...**\n`{get_progress_bar(60)}`", 
                    "parse_mode": "Markdown"
                })

            # Nick Bot ke response ka wait karo
            await conv.get_response() # Processing msg skip
            response = await conv.get_response() # Final link msg
            raw_text = response.text

            all_urls = re.findall(r'https?://[^\s]+', raw_text)
            
            if len(all_urls) >= 2:
                # Completed status
                if p_id:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                        "chat_id": chat_id, "message_id": p_id,
                        "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", 
                        "parse_mode": "Markdown"
                    })
                
                final_text = (
                    "✅ **BYPASSED!**\n\n"
                    f"**ORIGINAL LINK:**\n{all_urls[0]}\n\n"
                    f"**BYPASSED LINK:**\n{all_urls[1]}"
                )
            else:
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@sandibypassbot")

            # Final Result display
            if p_id:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                    "chat_id": chat_id, "message_id": p_id,
                    "text": final_text, "parse_mode": "Markdown", 
                    "disable_web_page_preview": True
                })
                
    except Exception as e:
        if p_id:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"
            })
    finally:
        await client.disconnect()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    message = data.get("message") or data.get("edited_message")
    
    if message and "text" in message:
        chat_id = message["chat"]["id"]
        text = message["text"]
        mid = message["message_id"]

        if text.startswith("/start"):
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "✅ Bot is Ready!"})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            # Vercel fix: background task start karne ke liye
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.create_task(process_bypass(chat_id, mid, urls[0]))

    return "ok", 200

@app.route('/')
def home():
    return "Bot is Alive and Fast!"
