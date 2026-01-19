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
TARGET_BOT = "nick_bypass_bot" # Username without @ for entity fetch

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
    # INITIAL STATUS
    status_resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"⏳ **Launching Mini App (Human Simulation)...**\n`{get_progress_bar(15)}`",
        "reply_to_message_id": message_id, "parse_mode": "Markdown"
    }).json()
    p_id = status_resp.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.connect()
    
    try:
        # 1. GET FULL BOT ENTITY (Fixes "Not a valid bot" error)
        # Isse Telegram ko bot ki ID aur Access Hash mil jati hai
        bot = await client.get_entity(TARGET_BOT)
        
        # 2. SIMULATE CLICKING: https://t.me/Nick_Bypass_Bot?startapp=go
        # Hum RequestWebViewRequest use karenge jo 'startapp' parameters handle karta hai
        await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform="android",
            start_param="go", # Ye 'go' wahi hai jo startapp=go mein hai
            from_bot_menu=False
        ))
        
        # 3. HUMAN WAIT (Page loading simulation)
        # 5-8 seconds rukna zaroori hai taaki Nick Bot ko lage ki koi real user hai
        wait_time = random.randint(6, 9)
        bot_request(token, "editMessageText", {
            "chat_id": chat_id, "message_id": p_id,
            "text": f"⏳ **Verifying on Mini App Page ({wait_time}s)...**\n`{get_progress_bar(40)}`", 
            "parse_mode": "Markdown"
        })
        await asyncio.sleep(wait_time)

        # 4. SEND /START (Finalizing the flow)
        async with client.conversation(bot, timeout=300) as conv:
            await conv.send_message("/start")
            
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"✅ **Verification Success! Bypassing...**\n`{get_progress_bar(65)}`", 
                "parse_mode": "Markdown"
            })
            
            # 5. SEND THE LINK
            await conv.send_message(user_url)
            response = await conv.get_response()

            # Wait for second response if bot sends "Processing" first
            if "https" not in (response.text or ""):
                response = await conv.get_response()

            # CLEANING AND SENDING RESULT
            raw_text = response.text or ""
            urls = re.findall(r'https?://[^\s]+', raw_text)

            if len(urls) >= 2:
                final_text = f"✅ **BYPASS COMPLETED**\n\n**Original:** {urls[0]}\n**Bypassed:** {urls[1]}"
            else:
                final_text = re.sub(r'(?i)Powered By.*|@\w+', '', raw_text).strip()

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": final_text if final_text else "⚠️ Bypass Failed.",
                "parse_mode": "Markdown", "disable_web_page_preview": True
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
def home(): return "Sandi Bot is Online"
