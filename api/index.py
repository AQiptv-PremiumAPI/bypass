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

# --- HELPERS ---
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
    initial_resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"⏳ **Bypass Started...**\n`{get_progress_bar(10)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    p_id = initial_resp.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=300) as conv:
            await conv.send_message(user_url)
            response = await conv.get_response()

            # --- DETECTION LOGIC ---
            is_mini_app = "Open The Mini App" in (response.text or "")
            is_captcha = response.photo or "Human Verification Required" in (response.text or "")

            # 1. CAPTCHA HANDLING (AS BEFORE)
            if is_captcha and response.photo:
                # ... (Same photo captcha code you have)
                pass 

            # 2. ADVANCED MINI APP BYPASS
            if is_mini_app:
                bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": "🛡️ **Triggering Deep Verification...**", "parse_mode": "Markdown"})
                
                # Nick Bot ke button se WebView URL extract karna
                web_view = await client(functions.messages.RequestWebViewRequest(
                    peer=TARGET_BOT,
                    bot=TARGET_BOT,
                    platform='android',
                    from_bot_menu=False,
                    url=response.reply_markup.rows[0].buttons[0].url if hasattr(response.reply_markup.rows[0].buttons[0], 'url') else None
                ))
                
                auth_url = web_view.url
                # Is URL ko 'visit' karna zaroori hai Nick Bot ko bewakoof banane ke liye
                requests.get(auth_url, timeout=10) 
                
                # Refresh link to trigger bot
                verified = False
                for _ in range(20):
                    await asyncio.sleep(2)
                    last_msgs = await client.get_messages(TARGET_BOT, limit=1)
                    if any(x in (last_msgs[0].text or "") for x in ["Successful", "Processing", "https"]):
                        verified = True
                        if "https" not in last_msgs[0].text:
                            await conv.send_message(user_url)
                            response = await conv.get_response()
                        else:
                            response = last_msgs[0]
                        break
                
                if not verified:
                    # Final Attempt: Force Start
                    await conv.send_message("/start")
                    await asyncio.sleep(2)
                    await conv.send_message(user_url)
                    response = await conv.get_response()

            # --- EXTRACTION & CLEANING ---
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⏳ **Finishing...**\n`{get_progress_bar(90)}`", "parse_mode": "Markdown"})
            
            # Loop jab tak link na mil jaye
            max_tries = 5
            while "https" not in (response.text or "") and max_tries > 0:
                response = await conv.get_response()
                max_tries -= 1

            raw_text = response.text or ""
            urls = re.findall(r'https?://[^\s]+', raw_text)
            
            if len(urls) >= 2:
                res_msg = f"**ORIGINAL LINK:**\n{urls[0]}\n\n**BYPASSED LINK:**\n{urls[1]}"
            else:
                res_msg = re.sub(r'(?i)Powered By.*|@\w+', '', raw_text).strip()

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": res_msg, "parse_mode": "Markdown", "disable_web_page_preview": True
            })

    except Exception as e:
        if p_id:
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ System Error: {str(e)}"})
    finally:
        await client.disconnect()

# --- WEBHOOKS ---
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
def home(): return "Deep Bypass Engine Live"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
