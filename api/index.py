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
# Make sure this session is valid and authorized
STRING_SESSION = "1BVtsOL0Bu53itjhCEqeLVhMJR8lAoN8lcsfm9fr3Snhw_pDLKv-l-uYOxBSh08CmjlvAohLi6A99TAJwEhS8ty-3GUqqKstUY9GncNLqpES9pd4lCxN-gnPQEe6WUHj9hJGO9Z-U39Msrt21xu-cPB-nI2FFHf2Cmgo_3nwB59zH8JzRKy4ceBRSVsaM_khK3-mMDmRfld-cLPtNs1t2vQ3I6JzUXER4yznCaW9-UXCHa4IDimIEcWKeKkHlPFbtwcLxFr7RWf-cA5mJB1CWB9NM1pKSe0SnY_hFDn-wgn54A25cQK72jmoJn74U1FJ94KFEPmplV_zwWgaFk3CeitwSszPK2mg="
TARGET_BOT = "@nick_bypass_bot"

RAW_TOKENS = os.environ.get('BOT_TOKEN', '')
TOKENS = [t.strip() for t in RAW_TOKENS.split(',') if t.strip()]

def bot_request(token, method, payload=None, files=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if files: return requests.post(url, data=payload, files=files, timeout=10)
        return requests.post(url, json=payload, timeout=10)
    except: return None

def get_progress_bar(percent):
    done = int(percent / 10)
    bar = "■" * done + "□" * (10 - done)
    return f"[{bar}] {percent}%"

async def handle_bypass(token, chat_id, message_id, user_url):
    # Initial Message
    resp = bot_request(token, "sendMessage", {
        "chat_id": chat_id, 
        "text": f"⏳ **Processing...**\n`{get_progress_bar(15)}`",
        "reply_to_message_id": message_id,
        "parse_mode": "Markdown"
    })
    
    if not resp or not resp.json().get("ok"): return
    p_id = resp.json()["result"]["message_id"]

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    try:
        async with client.conversation(TARGET_BOT, timeout=120) as conv:
            await conv.send_message(user_url)
            response = await conv.get_response()

            # Captcha Logic
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
                    'caption': "🔐 **Human Verification Required**\n\nClick the correct button below.",
                    'reply_markup': str({'inline_keyboard': kb}).replace("'", '"')
                }, files={'photo': ('captcha.jpg', img_data, 'image/jpeg')}).json()
                
                cap_id = cap_resp.get("result", {}).get("message_id")

                # Wait for Success
                verified = False
                for _ in range(30): # Reduced wait for Vercel limits
                    await asyncio.sleep(2)
                    last_msgs = await client.get_messages(TARGET_BOT, limit=1)
                    if last_msgs and ("Successful" in (last_msgs[0].text or "") or "http" in (last_msgs[0].text or "")):
                        verified = True
                        bot_request(token, "editMessageCaption", {
                            "chat_id": chat_id, "message_id": cap_id,
                            "caption": "✅ **Verification Successful!**",
                            "reply_markup": '{"inline_keyboard": []}'
                        })
                        # Re-send URL after verification
                        await conv.send_message(user_url)
                        response = await conv.get_response()
                        break
                if not verified: return

            # Final result extraction
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Finalizing...**\n`{get_progress_bar(90)}`", "parse_mode": "Markdown"
            })

            urls = re.findall(r'https?://[^\s]+', response.text)
            res_msg = f"✅ **Bypass Done:**\n{urls[1] if len(urls)>1 else response.text}"

            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": res_msg, "parse_mode": "Markdown", "disable_web_page_preview": True
            })

    except Exception as e:
        bot_request(token, "sendMessage", {"chat_id": chat_id, "text": f"❌ Error: {str(e)}"})
    finally:
        await client.disconnect()

@app.route('/webhook/<int:idx>', methods=['POST'])
def webhook(idx):
    if idx >= len(TOKENS): return "Invalid Token Index", 400
    
    data = request.get_json()
    token = TOKENS[idx]
    
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            # Running as a task to prevent blocking
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
            
    return "ok", 200

@app.route('/')
def home(): return "RioTV Bypass API is Live"
