import os
import asyncio
import requests
import re
import io
from flask import Flask, request
from telethon import TelegramClient
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
    try:
        if files:
            return requests.post(url, data=payload, files=files, timeout=10)
        return requests.post(url, json=payload, timeout=10)
    except:
        return None

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

# --- FAST CLICKER ---
async def solve_captcha_remote(btn_text):
    try:
        client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            return # Session expired
        
        # Sirf last message uthao (Fastest way)
        msgs = await client.get_messages(TARGET_BOT, limit=1)
        if msgs and msgs[0].reply_markup:
            await msgs[0].click(text=btn_text)
    except Exception as e:
        print(f"Click Error: {e}")
    finally:
        await client.disconnect()

async def get_and_animate(token, chat_id, message_id, user_msg_url):
    # STEP 1: PROCESSING (10%)
    resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, "text": f"⏳ **Processing...**\n`{get_progress_bar(10)}`",
        "reply_to_message_id": message_id, "parse_mode": "Markdown"
    })
    
    if not resp: return
    p_id = resp.json().get("result", {}).get("message_id")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()

    try:
        async with client.conversation(TARGET_BOT, timeout=200) as conv:
            await conv.send_message(user_msg_url)
            
            # Show "Extracting" immediately
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
            })
            
            response = await conv.get_response()

            # --- CAPTCHA DETECTED ---
            if response.photo or "Human Verification" in response.text:
                # Memory mein download (Fast)
                file_bytes = io.BytesIO()
                await client.download_media(response.photo, file=file_bytes)
                file_bytes.seek(0)

                keyboard = []
                if response.reply_markup:
                    for row in response.reply_markup.rows:
                        btn_row = []
                        for btn in row.buttons:
                            btn_row.append({'text': btn.text, 'callback_data': f"solve_{btn.text}"})
                        keyboard.append(btn_row)

                # Send Captcha to User
                bot_request(token, "sendPhoto", {
                    'chat_id': chat_id,
                    'caption': "⚡ **Quick Verify Required**\n\n👇 Click the matching character below:",
                    'reply_markup': str({'inline_keyboard': keyboard}).replace("'", '"')
                }, files={'photo': ('cap.jpg', file_bytes, 'image/jpeg')})
                
                # --- FAST CHECK LOOP (Every 1.5s) ---
                verified = False
                for _ in range(100): # 150 seconds max
                    await asyncio.sleep(1.5) # <--- UPDATED: Check fast
                    last_msgs = await client.get_messages(TARGET_BOT, limit=1)
                    
                    text_check = last_msgs[0].text if last_msgs[0].text else ""
                    
                    if "Verification Successful" in text_check or "Processing" in text_check:
                        verified = True
                        bot_request(token, "sendMessage", {"chat_id": chat_id, "text": "✅ **Verified!** Processing..."})
                        
                        # Agar result already aa gaya hai
                        if "https" in text_check:
                            response = last_msgs[0]
                        else:
                            # Wait for final link
                            try:
                                response = await conv.get_response(timeout=20)
                            except:
                                response = last_msgs[0]
                        break
                
                if not verified: raise Exception("Timeout: Click faster next time.")

            # STEP 3: BYPASSING (70%)
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"
            })

            # STEP 4: RESULT
            raw_text = response.text
            all_urls = re.findall(r'https?://[^\s]+', raw_text)
            
            if len(all_urls) >= 2:
                bot_request(token, "editMessageText", {
                    "chat_id": chat_id, "message_id": p_id,
                    "text": f"✅ **Completed!**\n`{get_progress_bar(100)}`", "parse_mode": "Markdown"
                })
                final_text = f"**ORIGINAL:**\n{all_urls[0]}\n\n**BYPASSED:**\n{all_urls[1]}"
            else:
                final_text = raw_text.replace("@Nick_Bypass_Bot", "@RioBypassBot")

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id, "text": final_text, 
                "parse_mode": "Markdown", "disable_web_page_preview": True
            })

    except Exception as e:
        if p_id:
            bot_request(token, "editMessageText", {"chat_id": chat_id, "message_id": p_id, "text": f"⚠️ Error: {str(e)}"})
    finally:
        await client.disconnect()

# --- ROUTES ---
@app.route('/webhook/<int:bot_idx>', methods=['POST'])
def webhook(bot_idx):
    if bot_idx >= len(TOKENS): return "ok", 200
    token = TOKENS[bot_idx]
    data = request.get_json()

    # CALLBACK (Button Click)
    if "callback_query" in data:
        cb = data["callback_query"]
        if cb["data"].startswith("solve_"):
            btn_text = cb["data"].split("_")[1]
            
            # 1. Instant UI Feedback
            bot_request(token, "answerCallbackQuery", {"callback_query_id": cb["id"], "text": f"Sending '{btn_text}'..."})
            
            # 2. Remote Click (Background)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(solve_captcha_remote(btn_text))
            loop.close()
        return "ok", 200

    # MESSAGE
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        if msg["text"].startswith("/start"):
            bot_request(token, "sendMessage", {"chat_id": msg["chat"]["id"], "text": "✅ Bot Active!"})
        else:
            urls = re.findall(r'https?://[^\s]+', msg["text"])
            if urls:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(get_and_animate(token, msg["chat"]["id"], msg["message_id"], urls[0]))
                loop.close()
    return "ok", 200

@app.route('/')
def home(): return "Fast Vercel Bot Running"
