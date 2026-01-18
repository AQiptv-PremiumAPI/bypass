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
    # 1. PEHLE PROCESSING DIKHANA HAI
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
                # Agar Captcha aaya toh Processing wala message delete kar do
                bot_request(token, "deleteMessage", {"chat_id": chat_id, "message_id": p_id})
                
                img_data = io.BytesIO()
                await client.download_media(response.photo, file=img_data)
                img_data.seek(0)

                kb = []
                if response.reply_markup:
                    for row in response.reply_markup.rows:
                        kb.append([{'text': b.text, 'callback_data': f"solve_{b.text}"} for b in row.buttons])

                # Send Captcha Image with Buttons
                cap_res = bot_request(token, "sendPhoto", {
                    'chat_id': chat_id,
                    'caption': "🔐 **Human Verification Required**\n\n👉 Solve the captcha to continue.",
                    'reply_markup': str({'inline_keyboard': kb}).replace("'", '"')
                }, files={'photo': ('captcha.jpg', img_data, 'image/jpeg')}).json()
                cap_msg_id = cap_res.get("result", {}).get("message_id")

                # Wait for Success
                verified = False
                for _ in range(150):
                    await asyncio.sleep(1.5)
                    last = await client.get_messages(TARGET_BOT, limit=1)
                    if "Verification Successful" in (last[0].text or ""):
                        verified = True
                        # Update Captcha Message: Remove Buttons, Change Text
                        bot_request(token, "editMessageCaption", {
                            "chat_id": chat_id, "message_id": cap_msg_id,
                            "caption": "✅ **Verification Successful!**\nNow processing your link...",
                            "reply_markup": str({'inline_keyboard': []})
                        })
                        # Phirse Processing start karna hai (New Message)
                        new_p = bot_request(token, "sendMessage", {
                            "chat_id": chat_id, "text": f"⏳ **Restarting Processing...**\n`{get_progress_bar(20)}`"
                        }).json()
                        p_id = new_p.get("result", {}).get("message_id")
                        
                        # Re-send Link to Nick Bot
                        await conv.send_message(user_url)
                        response = await conv.get_response()
                        break
                if not verified: return

            # --- START FINAL PROGRESS ANIMATION ---
            stages = [("Extracting", 40), ("Bypassing", 75)]
            for stage, pc in stages:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **{stage}...**\n`{get_progress_bar(pc)}`", "parse_mode": "Markdown"
                })
                await asyncio.sleep(1.5)

            # Wait for result if not already there
            if "https" not in (response.text or ""):
                response = await conv.get_response()

            # Final Completed (100%)
            urls = re.findall(r'https?://[^\s]+', response.text)
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
            })
            
            res_msg = f"**ORIGINAL LINK:**\n{urls[0]}\n\n**BYPASSED LINK:**\n{urls[1]}" if len(urls) >= 2 else response.text.replace("@Nick_Bypass_Bot", "@RioBypassBot")
            
            bot_request(token, "sendMessage", {
                "chat_id": chat_id, "text": res_msg, 
                "parse_mode": "Markdown", "disable_web_page_preview": True
            })

    except Exception as e:
        if p_id: bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
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
        if urls: asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "Sandi Bot is Online"
