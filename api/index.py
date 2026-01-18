import os
import asyncio
import requests
import re
import io
from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession

app = Flask(__name__)

# --- CONFIG ---
API_ID = 39707299
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
STRING_SESSION = "1BVtsOL0Bu4fBzpV-FhYXBcQcBA89IDoDqELmvjXfUSnIOLQemGxlvzFzDW4rz3gO815J0GOhOvNifnwEccgWnWmHa2KzYrJuKjVoYi1SbpgGJR8ZtOmxMSML7iJ0lnvxO7mNpiqtgKLGMe0PcQ6DqD6EwoZXQ57wDcLzR4LWCOgPaEQhgDPQpB_kf7qbNQSbD6ezSb2W9o1Wwn5i6WEvT-O_tzRz9e_DU_5zqwR_6dkXa0jTEFFxA0gxlqMgV8O2j3O3wnbLXKDPLEvVsTMBFro-_xhrZJ4nigeYAelp7rsKXYUBnqXTiovbKK4asOiJa8GqsVeqKoasEGo35vO7OTzXwpvlBEQ="
TARGET_BOT = "@nick_bypass_bot"
OCR_API_KEY = 'helloworld' # Yahan apni OCR.space API key dalein (Best performance ke liye apni lein)

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

# --- AUTO CAPTCHA SOLVER FUNCTION ---
def get_captcha_solution(img_bytes):
    try:
        payload = {
            'apikey': OCR_API_KEY,
            'language': 'eng',
            'isOverlayRequired': False,
            'OCREngine': 2 
        }
        files = {'filename': ('c.jpg', img_bytes, 'image/jpeg')}
        r = requests.post('https://api.ocr.space/parse/image', files=files, data=payload, timeout=10).json()
        if r.get('OCRExitCode') == 1:
            text = r['ParsedResults'][0]['ParsedText'].strip().upper()
            # Clean text to find single char
            chars = re.findall(r'[A-Z0-9]', text)
            return chars[0] if chars else None
    except: return None
    return None

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

            # --- AUTOMATIC CAPTCHA CHECK ---
            if response.photo or "Human Verification" in (response.text or ""):
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Solving Captcha...**\n`{get_progress_bar(30)}`", "parse_mode": "Markdown"
                })
                
                # Image download aur OCR solution
                img_data = await client.download_media(response.photo, file=bytes)
                solution = get_captcha_solution(img_data)
                
                if solution and response.reply_markup:
                    # Automatic click logic
                    clicked = False
                    for row in response.reply_markup.rows:
                        for button in row.buttons:
                            if button.text.strip().upper() == solution:
                                await response.click(text=button.text)
                                clicked = True
                                break
                    
                    if clicked:
                        # Wait for Verification Successful
                        for _ in range(20):
                            await asyncio.sleep(1.5)
                            last = await client.get_messages(TARGET_BOT, limit=1)
                            if "Verification Successful" in (last[0].text or "") or "Processing" in (last[0].text or ""):
                                response = last[0]
                                break

            # --- REST OF THE PROGRESS ANIMATION ---
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Extracting...**\n`{get_progress_bar(50)}`", "parse_mode": "Markdown"
            })
            
            await asyncio.sleep(1)

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Bypassing...**\n`{get_progress_bar(80)}`", "parse_mode": "Markdown"
            })

            if "https" not in (response.text or ""):
                response = await conv.get_response()

            # Completed (100%)
            urls = re.findall(r'https?://[^\s]+', response.text)
            if len(urls) >= 2:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                res_msg = f"**ORIGINAL LINK:**\n{urls[0]}\n\n**BYPASSED LINK:**\n{urls[1]}"
            else:
                res_msg = response.text.replace("@Nick_Bypass_Bot", "@riobypassbot")

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
        bot_request(token, "answerCallbackQuery", {"callback_query_id": data["callback_query"]["id"], "text": "Verifying..."})
        return "ok", 200

    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "Sandi Bot with Auto-Captcha & Smooth Progress is Live"
