import os
import asyncio
import requests
import re
import io
from flask import Flask, request
from telethon import TelegramClient, functions
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

async def solve_remote(btn_text):
    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        msgs = await client.get_messages(TARGET_BOT, limit=1)
        if msgs and msgs[0].reply_markup:
            await msgs[0].click(text=btn_text)

async def handle_bypass(token, chat_id, message_id, user_url):
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
            response = await conv.get_response()

            # --- CASE 1: IMAGE CAPTCHA ---
            if response.photo or "Human Verification Required" in (response.text or ""):
                if response.photo:
                    bot_request(token, "deleteMessage", {"chat_id": chat_id, "message_id": p_id})
                    img_data = io.BytesIO()
                    await client.download_media(response.photo, file=img_data)
                    img_data.seek(0)
                    kb = []
                    if response.reply_markup:
                        for row in response.reply_markup.rows:
                            kb.append([{'text': b.text, 'callback_data': f"solve_{b.text}"} for b in row.buttons])
                    cap_resp = bot_request(token, "sendPhoto", {
                        'chat_id': chat_id,
                        'caption': "🔐 Human Verification Required\n\n👉 Click the character inside the circle",
                        'reply_markup': str({'inline_keyboard': kb}).replace("'", '"')
                    }, files={'photo': ('captcha.jpg', img_data, 'image/jpeg')}).json()
                    cap_id = cap_resp.get("result", {}).get("message_id")

                    verified = False
                    for _ in range(150):
                        await asyncio.sleep(1.5)
                        last = await client.get_messages(TARGET_BOT, limit=1)
                        if any(x in (last[0].text or "") for x in ["Successful", "Processing", "https"]):
                            verified = True
                            bot_request(token, "editMessageCaption", {"chat_id": chat_id, "message_id": cap_id, "caption": "✅ Verified!"})
                            await conv.send_message(user_url)
                            response = await conv.get_response()
                            break
                    if not verified: return

            # --- CASE 2: MINI APP BYPASS (FIXED) ---
            if "Open The Mini App" in (response.text or ""):
                bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": "🛡️ **Emulating Mini App Session...**", "parse_mode": "Markdown"})
                
                if response.reply_markup:
                    # User-bot simulate karega Mini App open karne ka request
                    try:
                        app_button = response.reply_markup.rows[0].buttons[0]
                        # Ye niche wali line bot ko signal degi ki App "Open" ho gayi hai
                        await client(functions.messages.RequestWebViewRequest(
                            peer=TARGET_BOT,
                            bot=TARGET_BOT,
                            platform='android',
                            url=app_button.url if hasattr(app_button, 'url') else None,
                            from_bot_menu=False
                        ))
                    except Exception as web_err:
                        # Agar WebView fail ho toh normal click try karega
                        await response.click(0)

                    # Bot ko refresh hone ka time dena (Nick Bot 5-10 sec leta hai verify karne mein)
                    verified = False
                    for _ in range(25): # 50 seconds tak wait karega
                        await asyncio.sleep(2)
                        last_msgs = await client.get_messages(TARGET_BOT, limit=1)
                        check_text = last_msgs[0].text or ""
                        
                        # Agar bot 'Successful' bol de ya khud link bhej de
                        if any(x in check_text for x in ["Successful", "Processing", "https"]):
                            verified = True
                            if "https" not in check_text:
                                await conv.send_message(user_url)
                                response = await conv.get_response()
                            else:
                                response = last_msgs[0]
                            break
                    
                    if not verified:
                        raise Exception("Mini App verification timed out. Bot is not responding to app trigger.")

            # --- FINAL STEP: EXTRACTION ---
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⏳ **Extracting...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"})
            
            if "https" not in (response.text or ""):
                response = await conv.get_response()

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
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook/<int:idx>', methods=['POST'])
def webhook(idx):
    data = request.get_json()
    token = TOKENS[idx]
    if "callback_query" in data:
        btn = data["callback_query"]["data"].split("_")[1]
        asyncio.run(solve_remote(btn))
        return "ok", 200
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "Bot is Live with Fixed Mini App Logic"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
