from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import requests

app = Flask(__name__)

# --- CONFIGURATION ---
API_ID = 39707299 
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
BOT_TOKEN = '8374143251:AAGY5_QfDcr_PZ2b2zAoD8WMbXr1Hubm-jw'
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA=" 
TARGET_BOT = "@nick_bypass_bot"

async def get_final_reply(user_msg):
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    final_text = ""
    try:
        async with client.conversation(TARGET_BOT, timeout=45) as conv:
            await conv.send_message(user_msg)
            
            # Initial response
            response = await conv.get_response()
            final_text = response.text
            
            # Wait for final bypass link
            try:
                response = await conv.get_response(timeout=15)
                final_text = response.text
            except:
                pass

            # Branding Replacement
            if final_text:
                final_text = final_text.replace("@Nick_Bypass_Bot", "@sandi_bypass_bot")
                final_text = final_text.replace("@nick_bypass_bot", "@sandi_bypass_bot")
                final_text = final_text.replace("Nick Bypass Bot", "Sandi Bypass Bot")
                final_text = final_text.replace("Nick Bypass", "Sandi Bypass")
                
    except Exception as e:
        final_text = f"⚠️ Error: {str(e)}"
    finally:
        await client.disconnect()
    
    return final_text

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_msg = message["text"]
        message_id = message["message_id"]

        # 1. Start Command
        if user_msg == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "✅ *Bot Active!*\n\nSirf link (http/https) bhejiye bypass karne ke liye.", "reply_to_message_id": message_id, "parse_mode": "Markdown"})
            return "ok", 200

        # 2. URL Filter (Sirf http/https check)
        if not (user_msg.startswith("http://") or user_msg.startswith("https://")):
            # Agar URL nahi hai toh bot ignore karega
            return "ok", 200

        # 3. Bypass Process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            nick_reply = loop.run_until_complete(get_final_reply(user_msg))
            
            # 4. Group Reply Logic (reply_to_message_id use kiya hai)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={
                              "chat_id": chat_id, 
                              "text": nick_reply, 
                              "reply_to_message_id": message_id
                          })
        except:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "❌ Timeout! Nick Bot ne der kar di.", "reply_to_message_id": message_id})

    return "ok", 200

@app.route('/')
def home():
    return "Bot is Running with URL Filter and Group Reply!"
