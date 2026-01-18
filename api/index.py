import os
import asyncio
import requests
import re
from flask import Flask, request
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession

app = Flask(__name__)

# --- CONFIGURATION ---
API_ID = 39707299
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA="
TARGET_BOT = "@nick_bypass_bot"

RAW_TOKENS = os.environ.get('BOT_TOKEN', '')
TOKENS = [t.strip() for t in RAW_TOKENS.split(',') if t.strip()]

def bot_request(token, method, payload, files=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    if files:
        return requests.post(url, data=payload, files=files)
    return requests.post(url, json=payload)

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def solve_captcha_remote(btn_text):
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    async with client.conversation(TARGET_BOT) as conv:
        messages = await client.get_messages(TARGET_BOT, limit=1)
        if messages and messages[0].reply_markup:
            await messages[0].click(text=btn_text)
    await client.disconnect()

async def get_and_animate(token, chat_id, message_id, user_msg_url):
    # STEP 1: PROCESSING (10%)
    resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, "text": f"⏳ **Processing...**\n`{get_progress_bar(10)}`",
        "reply_to_message_id": message_id, "parse_mode": "Markdown"
    }).json()
    p_id = resp.get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()

    try:
        async with client.conversation(TARGET_BOT, timeout=300) as conv:
            await conv.send_message(user_msg_url)
            
            # STEP 2: EXTRACTING (40%)
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"})
            
            response = await conv.get_response()

            # --- CAPTCHA MIRRORING ---
            if response.photo or "Human Verification" in response.text:
                photo_path = await client.download_media(response.photo)
                
                # Nick Bot ke buttons mirror karna
                keyboard = []
                if response.reply_markup:
                    for row in response.reply_markup.rows:
                        btn_row = []
                        for btn in row.buttons:
                            btn_row.append({'text': btn.text, 'callback_data': f"solve_{btn.text}"})
                        keyboard.append(btn_row)

                with open(photo_path, 'rb') as f:
                    bot_request(token, "sendPhoto", {
                        'chat_id': chat_id,
                        'caption': "🔒 **Human Verification Required**\n\n👉 Click the **letter / number** inside the circle below:",
                        'reply_markup': str({'inline_keyboard': keyboard}).replace("'", '"')
                    }, files={'photo': f})
                
                # Check looping for success
                verified = False
                for _ in range(40): # 3 mins approx
                    await asyncio.sleep(5)
                    last_msgs = await client.get_messages(TARGET_BOT, limit=1)
                    if "Verification Successful" in last_msgs[0].text or "Processing" in last_msgs[0].text:
                        verified = True
                        bot_request(token, "sendMessage", {"chat_id": chat_id, "text": "✅ **Verification Successful!**"})
                        response = last_msgs[0] if "https" in last_msgs[0].text else await conv.get_response()
                        break
                if not verified: raise Exception("Captcha Timeout")

            # STEP 3: BYPASSING (70%)
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"})

            # STEP 4: COMPLETED (100%)
            raw_text = response.text
            all_urls = re.findall(r'https?://[^\s]+', raw_text)
            
            if len(all_urls) >= 2:
                bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"})
                final_text = f"**ORIGINAL LINK:**\n{all_urls[0]}\n\n**BYPASSED LINK:**\n{all_urls[1]}"
            else:
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@RioBypassBot")

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id, "text": final_text, 
                "parse_mode": "Markdown", "disable_web_page_preview": True
            })

    except Exception as e:
        bot_request(token, "sendMessage", {"chat_id": chat_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook/<int:bot_idx>', methods=['POST'])
def webhook(bot_idx):
    if bot_idx >= len(TOKENS): return "ok", 200
    token = TOKENS[bot_idx]
    data = request.get_json()

    if "callback_query" in data:
        cb = data["callback_query"]
        if cb["data"].startswith("solve_"):
            btn_text = cb["data"].split("_")[1]
            asyncio.run(solve_captcha_remote(btn_text))
            bot_request(token, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Verifying..."})
        return "ok", 200

    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        if msg["text"].startswith("/start"):
            bot_request(token, "sendMessage", {"chat_id": msg["chat"]["id"], "text": "✅ Bot Active! Send a link."})
        else:
            urls = re.findall(r'https?://[^\s]+', msg["text"])
            if urls:
                asyncio.run(get_and_animate(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "Multi-Bot Live"
