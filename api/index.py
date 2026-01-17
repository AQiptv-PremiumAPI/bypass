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

async def get_and_animate(chat_id, message_id, user_msg_url):
    # Initial Message
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
            
            # Progress update
            if processing_msg_id:
                bot_request("editMessageText", {
                    "chat_id": chat_id, "message_id": processing_msg_id,
                    "text": f"⏳ **Bypassing...**\n`{get_progress_bar(60)}`", "parse_mode": "Markdown"
                })

            # Nick Bot response wait
            # Hum loop chalayenge taki 'Processing' message ke baad final result pakad sakein
            raw_text = ""
            for _ in range(15): # Max 15 seconds wait
                response = await conv.get_response()
                if "Bypassed Link" in response.text or "Original Link" in response.text:
                    raw_text = response.text
                    break
                await asyncio.sleep(1)

            # --- IMPROVED EXTRACTION LOGIC ---
            bypass_content = ""
            
            # 1. Sabse pehle 'Bypassed Link :┖' ke baad ka text dhoondo
            match = re.search(r"Bypassed Link\s*:[^h{]*([h{].*?)(?:\n|Time Taken|$)", raw_text, re.DOTALL)
            
            if match:
                bypass_content = match.group(1).strip()
            else:
                # 2. Agar regex fail ho toh manual split try karo
                if "Bypassed Link" in raw_text:
                    after_bypass = raw_text.split("Bypassed Link")[-1]
                    # '┖' symbol ko remove karo agar hai toh
                    clean_after = after_bypass.replace(":", "").replace("┖", "").strip()
                    bypass_content = clean_after.split("\n")[0].strip()

            # Final Format
            final_text = (
                "✅ **BYPASSED!**\n\n"
                "**ORIGINAL LINK:**\n"
                f"{user_msg_url}\n\n"
                "**BYPASSED LINK:**\n"
                f"{bypass_content if bypass_content else '❌ Not Found'}"
            )

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
            bot_request("sendMessage", {"chat_id": chat_id, "text": "✅ Bot is Ready! Send me a link."})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_and_animate(chat_id, mid, urls[0]))

    return "ok", 200

@app.route('/')
def home():
    return "Bot is Online"

if __name__ == '__main__':
    app.run(port=5000)
