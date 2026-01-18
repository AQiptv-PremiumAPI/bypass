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
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA="
TARGET_BOT = "@nick_bypass_bot"

# Force Join Channels
CHANNELS = ["@riotvnetwork", "@riotv_bypass"]

RAW_TOKENS = os.environ.get('BOT_TOKEN', '')
TOKENS = [t.strip() for t in RAW_TOKENS.split(',') if t.strip()]

def bot_request(token, method, payload, files=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if files: return requests.post(url, data=payload, files=files, timeout=15)
        return requests.post(url, json=payload, timeout=15)
    except: return None

# --- NEW: Check if user joined channels ---
def check_join(token, user_id):
    for channel in CHANNELS:
        res = bot_request(token, "getChatMember", {"chat_id": channel, "user_id": user_id})
        if res:
            status = res.json().get("result", {}).get("status", "")
            if status not in ["creator", "administrator", "member"]:
                return False
    return True

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def solve_remote(btn_text):
    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        msgs = await client.get_messages(TARGET_BOT, limit=1)
        if msgs and msgs[0].reply_markup:
            await msgs[0].click(text=btn_text)

async def handle_bypass(token, chat_id, message_id, user_url, user_id):
    # --- 1. FORCE JOIN CHECK ---
    if not check_join(token, user_id):
        kb = {"inline_keyboard": [
            [{"text": "Join Channel 1", "url": "https://t.me/riotvnetwork"}],
            [{"text": "Join Channel 2", "url": "https://t.me/riotv_bypass"}]
        ]}
        bot_request(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "❌ **Access Denied!**\n\nYou must join our channels to use this bot. After joining, send the link again.",
            "reply_markup": kb,
            "reply_to_message_id": message_id
        })
        return

    # 2. ALWAYS SHOW PROCESSING FIRST
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

            # --- CHECK FOR CAPTCHA ---
            if response.photo or "Human Verification" in (response.text or ""):
                img_data = io.BytesIO()
                await client.download_media(response.photo, file=img_data)
                img_data.seek(0)

                kb = []
                if response.reply_markup:
                    for row in response.reply_markup.rows:
                        kb.append([{'text': b.text, 'callback_data': f"solve_{b.text}"} for b in row.buttons])

                bot_request(token, "sendPhoto", {
                    'chat_id': chat_id,
                    'caption': "🔐 **Human Verification Required**\n\n👉 Click the letter/number inside the circle below:",
                    'reply_markup': str({'inline_keyboard': kb}).replace("'", '"')
                }, files={'photo': ('captcha.jpg', img_data, 'image/jpeg')})

                verified = False
                for _ in range(150):
                    await asyncio.sleep(1.5)
                    last = await client.get_messages(TARGET_BOT, limit=1)
                    msg_text = last[0].text or ""
                    if "Verification Successful" in msg_text or "Processing" in msg_text or "https" in msg_text:
                        verified = True
                        # Re-send logic if verification successful
                        if "Verification Successful" in msg_text:
                            bot_request(token, "sendMessage", {"chat_id": chat_id, "text": "✅ **Verification Successful!** Restarting..."})
                            await conv.send_message(user_url)
                            response = await conv.get_response()
                        else:
                            response = last[0]
                        break
                if not verified: return

            # --- START PROGRESS ANIMATION ---
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

            # Completed (100%)
            urls = re.findall(r'https?://[^\s]+', response.text)
            if len(urls) >= 2:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                res_msg = f"**ORIGINAL LINK:**\n{urls[0]}\n\n**BYPASSED LINK:**\n{urls[1]}"
            else:
                res_msg = response.text.replace("@Nick_Bypass_Bot", "@SandiBypassBot")

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
        user_id = msg["from"]["id"]
        
        # /start command check with Force Join
        if msg["text"] == "/start":
            if not check_join(token, user_id):
                kb = {"inline_keyboard": [
                    [{"text": "Join Channel 1", "url": "https://t.me/riotvnetwork"}],
                    [{"text": "Join Channel 2", "url": "https://t.me/riotv_bypass"}]
                ]}
                bot_request(token, "sendMessage", {
                    "chat_id": msg["chat"]["id"],
                    "text": "👋 Welcome! Please join our channels to use this bot.",
                    "reply_markup": kb
                })
            else:
                bot_request(token, "sendMessage", {"chat_id": msg["chat"]["id"], "text": "✅ Bot is ready! Send me a link."})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0], user_id))
    return "ok", 200

@app.route('/')
def home(): return "Sandi Bot with Force Join & Re-send Logic Active"
