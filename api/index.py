import os
import asyncio
import requests
import re
import random
from flask import Flask, request
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession

app = Flask(__name__)

# --- CONFIG ---
API_ID = 39707299
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
STRING_SESSION = "1BVtsOK0Buy2Axso-fI5CfSyMqHiK_P9ew-fP-PXrLs0gSRdXVv2hADcvnqoDp-ECKh5A0sy-IRnHefoH0bHgU3OlwpKYxiqB1hw6jUMIbgEbZplCTPlvoccvoxfZfXL9d_cZVcEch6m3Svs0DrAV4doqUMAmkgAXQHq-i84Nms-d-sGwMfuxf0R6npCtZyxzMPUGD5ODrwORywAm_Z_f1x2WvhHrIYKi5R1CXLzL2Zl56ylNot5eOKR-JXNoybuJYaQNuLtCxZ5OR875Zd9uXmeUQkhogp-xUMwbdcTyKMYZ_fhghilGuQhRJAaZYGXBJGTglf5uBRW_vuTbEuDn1tcc62QZrGU="
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
    # 1. INITIAL STATUS
    status_msg = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"🎭 **Simulating Human Interaction...**\n`{get_progress_bar(10)}`",
        "reply_to_message_id": message_id, "parse_mode": "Markdown"
    }).json()
    p_id = status_msg.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        # --- HUMAN SIMULATION START ---
        bot = await client.get_input_entity(TARGET_BOT)
        
        # Step 1: Open Mini App (startapp=go)
        # Isse Telegram ke backend ko signal jayega ki user ne App Page khola hai
        await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            start_param="go",
            from_bot_menu=False
        ))
        
        # Step 2: "Stay" on Mini App Page (Human behavior)
        # Hum 5-8 seconds tak rukenge taaki Nick Bot ko lage ki user ad dekh raha hai/page load kar raha hai
        wait_time = random.randint(5, 8)
        bot_request(token, "editMessageText", {
            "chat_id": chat_id, "message_id": p_id,
            "text": f"⏳ **Staying on Mini App for {wait_time}s...**\n`{get_progress_bar(25)}`", "parse_mode": "Markdown"
        })
        await asyncio.sleep(wait_time)

        # Step 3: Send /start to finalize (Finalizing human action)
        async with client.conversation(TARGET_BOT, timeout=300) as conv:
            await conv.send_message("/start")
            
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"✅ **Verification Done! Bypassing...**\n`{get_progress_bar(50)}`", "parse_mode": "Markdown"
            })
            
            # Step 4: Send the actual URL
            await conv.send_message(user_url)
            response = await conv.get_response()

            # --- EXTRACTING RESULTS ---
            if "https" not in (response.text or ""):
                response = await conv.get_response()

            raw_text = response.text or ""
            urls = re.findall(r'https?://[^\s]+', raw_text)

            if len(urls) >= 2:
                res_msg = f"✅ **SUCCESS!**\n\n**Original:** {urls[0]}\n**Bypassed:** {urls[1]}"
            else:
                clean_text = re.sub(r'(?i)Powered By.*|@\w+', '', raw_text).strip()
                res_msg = clean_text if clean_text else "⚠️ Bypass Failed."

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
def home(): return "Sandi Bot Human-Simulation is Active"
