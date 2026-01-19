import os
import asyncio
import requests
import re
import io
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

def bot_request(token, method, payload, files=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if files: return requests.post(url, data=payload, files=files, timeout=15)
        return requests.post(url, json=payload, timeout=15)
    except: return None

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def handle_bypass(token, chat_id, message_id, user_url):
    # 1. PEHLA STATUS
    initial_resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"⏳ **Opening Mini App Verification...**\n`{get_progress_bar(5)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    p_id = initial_resp.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        # --- YE SECTION HAR BAAR MINI APP LINK (startapp=go) PAR JAYEGA ---
        bot_peer = await client.get_input_entity(TARGET_BOT)
        
        # Simulating clicking the link: https://t.me/Nick_Bypass_Bot?startapp=go
        # Isse bot ko signal mil jayega ki aapne app open kar liya hai
        await client(functions.messages.RequestAppWebViewRequest(
            peer=bot_peer,
            app=types.InputBotAppShortName(bot_id=bot_peer, short_name="go"),
            platform="android",
            start_param="go",
            write_allowed=True
        ))
        
        # Nick Bot ko verify karne ka time dene ke liye thoda wait
        await asyncio.sleep(3) 

        async with client.conversation(TARGET_BOT, timeout=300) as conv:
            # 2. BYPASS START KARO
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Verification Done. Bypassing Link...**\n`{get_progress_bar(30)}`", 
                "parse_mode": "Markdown"
            })
            
            await conv.send_message(user_url)
            response = await conv.get_response()

            # --- SMOOTH PROGRESS ---
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Extracting Data...**\n`{get_progress_bar(60)}`", "parse_mode": "Markdown"
            })
            await asyncio.sleep(1)

            if "https" not in (response.text or ""):
                response = await conv.get_response()

            # --- CLEANING LOGIC ---
            raw_text = response.text or ""
            clean_text = re.sub(r'(?i)Powered By\s*@\w+', '', raw_text)
            clean_text = clean_text.replace("@Nick_Bypass_Bot", "").replace("@riobypassbot", "").strip()

            urls = re.findall(r'https?://[^\s]+', raw_text)
            if len(urls) >= 2:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                res_msg = f"**ORIGINAL LINK:**\n{urls[0]}\n\n**BYPASSED LINK:**\n{urls[1]}"
            else:
                res_msg = clean_text if clean_text else "⚠️ Verification success but bypass failed."

            res_msg = re.sub(r'(?i)Powered By.*', '', res_msg).strip()

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
    token = TOKENS[idx]
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "Sandi Bot with Auto Mini-App Verification is Live"
