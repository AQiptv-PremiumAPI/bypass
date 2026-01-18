import os
import asyncio
import requests
import re
import io
from flask import Flask, request
from telethon import TelegramClient, events
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
        if files: return requests.post(url, data=payload, files=files, timeout=20)
        return requests.post(url, json=payload, timeout=20)
    except: return None

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def solve_remote(btn_text):
    async with TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH) as client:
        # Nick bot ke last message par click karega
        msgs = await client.get_messages(TARGET_BOT, limit=1)
        if msgs and msgs[0].reply_markup:
            await msgs[0].click(text=btn_text)

async def handle_bypass(token, chat_id, message_id, user_url):
    # 1. Processing message start
    p_msg = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"⏳ **Processing...**\n`{get_progress_bar(15)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    }).json()
    p_id = p_msg.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=300) as conv:
            await conv.send_message(user_url)
            
            # Nick Bot ke response ka wait
            response = await conv.get_response()

            # --- CAPTCHA DETECTION FIX ---
            # Agar message mein photo hai ya "Human Verification" likha hai
            if response.photo or (response.text and "Verification Required" in response.text):
                # Processing msg delete karo captcha dikhane se pehle
                bot_request(token, "deleteMessage", {"chat_id": chat_id, "message_id": p_id})
                
                # Photo download karo
                img_path = await response.download_media(file=io.BytesIO())
                img_path.seek(0)

                # Buttons nikaalo
                kb = []
                if response.reply_markup:
                    for row in response.reply_markup.rows:
                        btn_row = []
                        for btn in row.buttons:
                            btn_row.append({'text': btn.text, 'callback_data': f"solve_{btn.text}"})
                        kb.append(btn_row)

                # Apne bot mein forward karo
                cap_res = bot_request(token, "sendPhoto", {
                    'chat_id': chat_id,
                    'caption': "🔐 **Human Verification Required**\n\n👉 Click the letter/number inside the circle\n\n⏳ Valid for 15 minutes",
                    'reply_markup': str({'inline_keyboard': kb}).replace("'", '"')
                }, files={'photo': ('captcha.jpg', img_path, 'image/jpeg')}).json()
                
                cap_msg_id = cap_res.get("result", {}).get("message_id")

                # Solution Check Loop
                solved = False
                for _ in range(100): # 2-3 mins wait
                    await asyncio.sleep(2)
                    last_msgs = await client.get_messages(TARGET_BOT, limit=1)
                    if last_msgs and "Verification Successful" in (last_msgs[0].text or ""):
                        solved = True
                        # Update Captcha UI
                        bot_request(token, "editMessageCaption", {
                            "chat_id": chat_id, "message_id": cap_msg_id,
                            "caption": "✅ **Verification Successful!**\nRestarting bypass process...",
                            "reply_markup": str({'inline_keyboard': []})
                        })
                        # Restart Processing
                        new_p = bot_request(token, "sendMessage", {"chat_id": chat_id, "text": f"⏳ **Restarting...**\n`{get_progress_bar(20)}`"}).json()
                        p_id = new_p.get("result", {}).get("message_id")
                        
                        # Re-send link after success
                        await conv.send_message(user_url)
                        response = await conv.get_response()
                        break
                
                if not solved: return

            # --- PROGRESS ANIMATION ---
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⏳ **Extracting...**\n`{get_progress_bar(50)}`", "parse_mode": "Markdown"})
            await asyncio.sleep(1)
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⏳ **Bypassing...**\n`{get_progress_bar(80)}`", "parse_mode": "Markdown"})

            # Result handling
            if "https" not in (response.text or ""):
                response = await conv.get_response()

            urls = re.findall(r'https?://[^\s]+', response.text)
            final_text = f"✅ **Completed!**\n\n**ORIGINAL:** {urls[0]}\n**BYPASSED:** {urls[1]}" if len(urls) >= 2 else response.text.replace("@Nick_Bypass_Bot", "@YourBot")
            
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": final_text, "parse_mode": "Markdown", "disable_web_page_preview": True})

    except Exception as e:
        if p_id: bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook/<int:idx>', methods=['POST'])
def webhook(idx):
    data = request.get_json()
    token = TOKENS[idx]
    if "callback_query" in data:
        btn_text = data["callback_query"]["data"].split("_")[1]
        asyncio.run(solve_remote(btn_text))
        bot_request(token, "answerCallbackQuery", {"callback_query_id": data["callback_query"]["id"], "text": "Sending click to Nick Bot..."})
        return "ok", 200
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls: asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "Bot is Live"
