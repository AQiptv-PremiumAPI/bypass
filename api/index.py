import os
from flask import Flask, request
from telethon import TelegramClient, events, types
from telethon.sessions import StringSession
import asyncio
import requests
import re

app = Flask(__name__)

# --- CONFIGURATION ---
API_ID = 39707299 
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA=" 
TARGET_BOT = "@nick_bypass_bot"

RAW_TOKENS = os.environ.get('BOT_TOKEN', '')
TOKENS = [t.strip() for t in RAW_TOKENS.split(',') if t.strip()]

def bot_request(token, method, payload):
    return requests.post(f"https://api.telegram.org/bot{token}/{method}", json=payload)

def get_progress_bar(percent):
    done = int(percent / 10)
    remain = 10 - done
    bar = "■" * done + "□" * remain
    return f"[{bar}] {percent}%"

async def get_and_animate(token, chat_id, message_id, user_msg_url):
    # STEP 1: Processing (10%)
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
            
            # STEP 2: Extracting (40%)
            if p_id:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
                })

            response = await conv.get_response()

            # --- CAPTCHA CHECK ---
            if "Human Verification" in response.text or response.photo:
                photo = await client.download_media(response.photo)
                buttons_markup = []
                if response.reply_markup:
                    for row in response.reply_markup.rows:
                        current_row = []
                        for btn in row.buttons:
                            current_row.append({'text': btn.text, 'callback_data': f"solve_{btn.text}"})
                        buttons_markup.append(current_row)

                with open(photo, 'rb') as f:
                    requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", 
                        files={'photo': f},
                        data={
                            'chat_id': chat_id,
                            'caption': "🔒 **Human Verification Required**\n\n👉 Click the **letter / number** inside the circle\n⌛ Valid for 15 minutes",
                            'reply_markup': str({'inline_keyboard': buttons_markup}).replace("'", '"')
                        }
                    )
                
                # Wait for user click
                for _ in range(60): 
                    await asyncio.sleep(5)
                    msgs = await client.get_messages(TARGET_BOT, limit=1)
                    if "Verification Successful" in msgs[0].text or "Processing" in msgs[0].text:
                        break
                
                # Verification Successful update
                if p_id:
                    bot_request(token, "editMessageText", {
                        "chat_id": chat_id, "message_id": p_id,
                        "text": f"✅ **Verification Successful!**\n`{get_progress_bar(60)}`", "parse_mode": "Markdown"
                    })
                
                # Re-check for bypassing response
                response = await conv.get_response()

            # STEP 3: Bypassing (70%)
            if p_id:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"
                })

            # Wait for final result
            if "https" not in response.text:
                response = await conv.get_response()

            # STEP 4: Completed (100%)
            if p_id:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })

            raw_text = response.text
            all_urls = re.findall(r'https?://[^\s]+', raw_text)
            if len(all_urls) >= 2:
                final_text = f"**ORIGINAL LINK:**\n{all_urls[0]}\n\n**BYPASSED LINK:**\n{all_urls[1]}"
            else:
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@RioBypassBot")

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": final_text, "parse_mode": "Markdown", "disable_web_page_preview": True
            })
                
    except Exception as e:
        if p_id:
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook/<int:bot_idx>', methods=['POST'])
def webhook(bot_idx):
    if bot_idx >= len(TOKENS): return "Bot not found", 404
    token = TOKENS[bot_idx]
    data = request.get_json()
    
    if "callback_query" in data:
        cb = data["callback_query"]
        if cb["data"].startswith("solve_"):
            btn_text = cb["data"].split("_")[1]
            async def remote_click():
                client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
                await client.start()
                msg = await client.get_messages(TARGET_BOT, limit=1)
                if msg and msg[0].reply_markup:
                    await msg[0].click(text=btn_text)
                await client.disconnect()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(remote_click())
            bot_request(token, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": "Verifying..."})
        return "ok", 200

    if data and "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(get_and_animate(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home():
    return f"Status: {len(TOKENS)} Bots Online."

app = app
