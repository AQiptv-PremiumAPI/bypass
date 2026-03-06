import os
import asyncio
import requests
import re
from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

# --- CONFIG ---
API_ID = 39707299
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
STRING_SESSION = "1BVtsOL0Bu7PInhUC3PWFzqTflouCeOIGJM3pCNYP3_cUnHbS0JBAWdwVZ3msRiaCDXCYDb8mYCkjm99in6fAYeHcM3GPkNks8MllhaQw8OPMzrMLkFvXmvnC8G6kdc9JZad82jZ6-7GHFGW7bZPDfH56hzC9hAhxnQvx35yfvQi3OBphr0jBAbIdgGu8Q3Oh3PRZEkyRPIFj4MRC6UQY-fTgXqE1SgtYH4RGu8hMcsWstNoyY1lmUFgVDg7l0Dmzryhs5bP3rDIbcScSLH0e999Ph0chas3N_OAJ7cVoklA6ZbWUE8Hti_N3Te2-GFQ7KjP2a3Kwmglmf5l6akmHKMN_GeFmTkU="
TARGET_BOT = "@nick_bypass_bot"

RAW_TOKENS = os.environ.get('BOT_TOKEN', '')
TOKENS = [t.strip() for t in RAW_TOKENS.split(',') if t.strip()]

def bot_request(token, method, payload):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try: return requests.post(url, json=payload, timeout=15)
    except: return None

def get_progress_bar(percent):
    done = int(percent / 10)
    return f"[{'■' * done}{'□' * (10 - done)}] {percent}%"

async def handle_bypass(token, chat_id, message_id, user_url):
    # 1. TAG USER & START PROCESSING
    initial_resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"⏳ **Processing...**\n`{get_progress_bar(15)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    p_id = initial_resp.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=300) as conv:
            await conv.send_message(user_url)
            
            # Extracting (40%)
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
            })
            
            response = await conv.get_response()

            # Bypassing (70%)
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"
            })
            
            # Wait for actual result if first response is just "Processing"
            if "Bypassed Link" not in (response.text or "") and "No Script Found" not in (response.text or ""):
                try:
                    response = await conv.get_response()
                except:
                    pass

            # --- UPDATED EXTRACTION LOGIC ---
            text = response.text or ""
            
            if "No Script Found for:" in text:
                # Handling the special case for unsupported scripts
                clean_url = user_url.strip()
                res_msg = f"⚠️ **No Script Found for:**\n\n{clean_url}"
            
            elif "Bypassed Link :" in text:
                # Extract everything after "Bypassed Link :" until the next newline or separator
                parts = text.split("Bypassed Link :")
                result_part = parts[1].split("Time Taken")[0].split("Search Any")[0].strip()
                # Clean up the emoji ✅ if present at the start
                result_part = result_part.replace("✅", "").strip()
                res_msg = f"✅ **Bypassed Ads**\n`{result_part}`"
            else:
                # Fallback to old URL method or plain text clean up
                urls = re.findall(r'https?://[^\s]+', text)
                if len(urls) >= 2:
                    res_msg = f"✅ **Bypassed Ads**\n{urls[1]}"
                else:
                    res_msg = text.replace("@Nick_Bypass_Bot", "@riobypassbot")

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": res_msg, "parse_mode": "Markdown", "disable_web_page_preview": True
            })

    except Exception as e:
        if p_id:
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook/<int:idx>', methods=['POST'])
def webhook(idx):
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            asyncio.run(handle_bypass(TOKENS[idx], msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "RioTV Bypass Bot is Running"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
