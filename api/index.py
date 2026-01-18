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

                verified = False
                for _ in range(150):
                    await asyncio.sleep(1.5)
                    last = await client.get_messages(TARGET_BOT, limit=1)
                    msg_text = last[0].text or ""
                    
                    if "Verification Successful" in msg_text or "Processing" in msg_text or "https" in msg_text:
                        verified = True
                        bot_request(token, "editMessageCaption", {
                            "chat_id": chat_id, "message_id": cap_id,
                            "caption": "✅ Captcha Verification Successful!",
                            "reply_markup": '{"inline_keyboard": []}'
                        })
                        await conv.send_message(user_url)
                        response = await conv.get_response()
                        break
                if not verified: return

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
            })
            await asyncio.sleep(1)

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"
            })

            if "https" not in (response.text or ""):
                response = await conv.get_response()

            # --- CLEANING LOGIC START ---
            raw_text = response.text or ""
            # Branding patterns remove karne ke liye
            clean_text = re.sub(r'(?i)Powered By\s*@\w+', '', raw_text) # Removes "Powered By @any_bot"
            clean_text = clean_text.replace("@Nick_Bypass_Bot", "").replace("@riobypassbot", "").strip()

            urls = re.findall(r'https?://[^\s]+', raw_text)
            if len(urls) >= 2:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                res_msg = f"**ORIGINAL LINK:**\n{urls[0]}\n\n**BYPASSED LINK:**\n{urls[1]}"
            else:
                res_msg = clean_text

            # Final check to ensure no branding remains
            res_msg = re.sub(r'(?i)Powered By.*', '', res_msg).strip()
            # --- CLEANING LOGIC END ---

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
