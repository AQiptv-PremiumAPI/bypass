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

RAW_TOKENS = os.environ.get('BOT_TOKEN', '')
TOKENS = [t.strip() for t in RAW_TOKENS.split(',') if t.strip()]

# Global Client for Real-time Response
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

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
    # Uses the already connected global client (Instant)
    if not client.is_connected():
        await client.connect()
    msgs = await client.get_messages(TARGET_BOT, limit=1)
    if msgs and msgs[0].reply_markup:
        await msgs[0].click(text=btn_text)

async def handle_bypass(token, chat_id, message_id, user_url):
    # 1. ALWAYS SHOW PROCESSING FIRST
    initial_resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"⏳ **Processing...**\n`{get_progress_bar(15)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    p_id = initial_resp.get("result", {}).get("message_id")

    if not client.is_connected():
        await client.connect()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=300) as conv:
            await conv.send_message(user_url)
            response = await conv.get_response()

            # --- CHECK FOR CAPTCHA ---
            if response.photo or "Human Verification" in (response.text or ""):
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
                    'caption': "🔐 Human Verification Required\n\n👉 Click the character inside the circle\n⏳ Valid for 15 minutes",
                    'reply_markup': str({'inline_keyboard': kb}).replace("'", '"')
                }, files={'photo': ('captcha.jpg', img_data, 'image/jpeg')}).json()
                cap_id = cap_resp.get("result", {}).get("message_id")

                # Fast Polling (0.7s) to detect Nick Bot response immediately
                verified = False
                for _ in range(200):
                    await asyncio.sleep(0.7) 
                    last_msgs = await client.get_messages(TARGET_BOT, limit=1)
                    msg_text = last_msgs[0].text or ""
                    
                    if any(x in msg_text for x in ["Successful", "Processing", "https"]):
                        verified = True
                        bot_request(token, "editMessageCaption", {
                            "chat_id": chat_id, "message_id": cap_id,
                            "caption": "✅ Captcha Verification Successful!",
                            "reply_markup": '{"inline_keyboard": []}'
                        })
                        
                        # Resubmit and set as p_id for progress bar
                        await conv.send_message(user_url)
                        response = await conv.get_response()
                        p_id = cap_id # Keep using the same message for success
                        break
                if not verified: return

            # --- START PROGRESS ANIMATION ---
            edit_method = "editMessageCaption" if response.photo else "editMessageText"
            content_key = "caption" if response.photo else "text"

            bot_request(token, edit_method, {
                "chat_id": chat_id, "message_id": p_id,
                content_key: f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
            })
            await asyncio.sleep(1)

            bot_request(token, edit_method, {
                "chat_id": chat_id, "message_id": p_id,
                content_key: f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"
            })

            if "https" not in (response.text or ""):
                response = await conv.get_response()

            # Completed (100%)
            urls = re.findall(r'https?://[^\s]+', response.text)
            if len(urls) >= 2:
                res_msg = f"✅ **Completed!**\n\n**ORIGINAL LINK:**\n{urls[0]}\n\n**BYPASSED LINK:**\n{urls[1]}"
            else:
                res_msg = response.text.replace("@Nick_Bypass_Bot", "@riobypassbot")

            bot_request(token, edit_method, {
                "chat_id": chat_id, "message_id": p_id,
                content_key: res_msg, "parse_mode": "Markdown", "disable_web_page_preview": True
            })

    except Exception as e:
        if p_id:
            bot_request(token, "sendMessage", {"chat_id": chat_id, "text": f"⚠️ Error: {str(e)}"})

@app.route('/webhook/<int:idx>', methods=['POST'])
def webhook(idx):
    data = request.get_json()
    token = TOKENS[idx]
    
    if "callback_query" in data:
        btn = data["callback_query"]["data"].split("_")[1]
        # Real-time Background Task
        asyncio.run(solve_remote(btn))
        bot_request(token, "answerCallbackQuery", {"callback_query_id": data["callback_query"]["id"], "text": "✅ Success! Nick Bot Notified."})
        return "ok", 200

    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

# Pre-connecting the client during startup
with client:
    client.loop.run_until_complete(client.connect())

@app.route('/')
def home(): return "Sandi Bot (Real-Time Mode) is Online"
