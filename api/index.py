from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import requests
import re
import time

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

async def get_and_animate(chat_id, message_id, user_msg_url):
    # Step 1: User ko pehla progress dikhana
    resp = bot_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"⏳ **Processing...**\n`{get_progress_bar(20)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    
    processing_msg_id = resp.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=60) as conv:
            await conv.send_message(user_msg_url)
            
            # Step 2: Progress update to 50%
            if processing_msg_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": processing_msg_id,
                    "text": f"⏳ **Bypassing...**\n`{get_progress_bar(50)}`", "parse_mode": "Markdown"
                })

            # Logic: Nick bot pehle 'Processing' bhejta hai, phir use EDIT karta hai.
            # Hum tab tak wait karenge jab tak "Original Link" text message mein na aa jaye.
            
            raw_text = ""
            max_retries = 10
            for _ in range(max_retries):
                response = await conv.get_response()
                raw_text = response.text
                if "Original Link" in raw_text:
                    break
                await asyncio.sleep(1) # Thoda wait agar bot processing dikha raha ho

            # --- EXTRACTION LOGIC ---
            bypass_result = "Not Found"
            
            if "Bypassed Link :┖" in raw_text:
                # ┖ ke baad ka content aur 'Time Taken' se pehle ka content
                parts = raw_text.split("Bypassed Link :┖")
                if len(parts) > 1:
                    content_after = parts[1]
                    bypass_result = content_after.split("Time Taken")[0].strip()
            
            # Final Formatting
            final_text = (
                "✅ **BYPASSED!**\n\n"
                "**ORIGINAL LINK:**\n"
                f"{user_msg_url}\n\n"
                "**BYPASSED LINK:**\n"
                f"{bypass_result}"
            )

            # Final Result ko Telegram pe bhejna
            if processing_msg_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, 
                    "message_id": processing_msg_id,
                    "text": final_text, 
                    "parse_mode": "Markdown", 
                    "disable_web_page_preview": True
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
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ **Bot Active!**\nSend any link to bypass."})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_and_animate(chat_id, mid, urls[0]))

    return "ok", 200

@app.route('/')
def home():
    return "Reliable Bypass Bot is Online!"

if __name__ == '__main__':
    app.run(port=5000)
