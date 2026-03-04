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
STRING_SESSION = "1BVtsOL0Bu53itjhCEqeLVhMJR8lAoN8lcsfm9fr3Snhw_pDLKv-l-uYOxBSh08CmjlvAohLi6A99TAJwEhS8ty-3GUqqKstUY9GncNLqpES9pd4lCxN-gnPQEe6WUHj9hJGO9Z-U39Msrt21xu-cPB-nI2FFHf2Cmgo_3nwB59zH8JzRKy4ceBRSVsaM_khK3-mMDmRfld-cLPtNs1t2vQ3I6JzUXER4yznCaW9-UXCHa4IDimIEcWKeKkHlPFbtwcLxFr7RWf-cA5mJB1CWB9NM1pKSe0SnY_hFDn-wgn54A25cQK72jmoJn74U1FJ94KFEPmplV_zwWgaFk3CeitwSszPK2mg="
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

async def handle_bypass(token, chat_id, message_id, user_url):
    # 1. INITIAL PROCESSING MESSAGE
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
            
            # --- PROGRESS ANIMATION ---
            # Extracting (40%)
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Extracting...**\n`{get_progress_bar(40)}`", "parse_mode": "Markdown"
            })
            
            response = await conv.get_response()

            # Bypassing (70%)
            bot_request(token, "editMessageText", {
                "chat_id": chat_id, "message_id": p_id,
                "text": f"⏳ **Bypassing...**\n`{get_progress_bar(70)}`", "parse_mode": "Markdown"
            })
            
            # If the first response doesn't have the link, wait for the next one
            if "https" not in (response.text or ""):
                response = await conv.get_response()

            # --- FINAL OUTPUT LOGIC ---
            urls = re.findall(r'https?://[^\s]+', response.text)
            
            # If 2 links found (Original & Bypassed), take the 2nd one
            if len(urls) >= 2:
                final_link = urls[1]
                res_msg = f"✅ **Bypassed Ads**\n{final_link}"
            else:
                # Fallback if logic changes
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
    
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        urls = re.findall(r'https?://[^\s]+', msg["text"])
        if urls:
            asyncio.run(handle_bypass(token, msg["chat"]["id"], msg["message_id"], urls[0]))
    return "ok", 200

@app.route('/')
def home(): return "RioTV Bypass Bot is Live"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
