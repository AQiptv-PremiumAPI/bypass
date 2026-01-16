from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import requests

app = Flask(__name__)

# --- CONFIGURATION ---
API_ID = 39707299 
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
BOT_TOKEN = '8532945131:AAHqyhgCC-sE1tO7kqOmy6jWJaxYCp2VBWE'
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA=" 
TARGET_BOT = "@nick_bypass_bot"

async def get_final_reply(user_msg):
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    final_text = ""
    try:
        async with client.conversation(TARGET_BOT, timeout=45) as conv:
            # Nick bot ko link bhejna
            await conv.send_message(user_msg)
            
            # Pehla msg (Processing...)
            response = await conv.get_response()
            
            # Dusra msg (As asli response)
            try:
                # 15 second wait for actual link
                response = await conv.get_response(timeout=15)
                final_text = response.text
            except:
                final_text = response.text

            # --- BRANDING REPLACEMENT ---
            # Jaisa msg Nick bot se aaya hai, waisa hi rahega bas naam badlega
            if final_text:
                final_text = final_text.replace("@Nick_Bypass_Bot", "@sandi_bypass_bot")
                final_text = final_text.replace("@nick_bypass_bot", "@sandi_bypass_bot")
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
                          json={
                              "chat_id": chat_id, 
                              "text": "✅ *Bot Active!*\n\nSirf `http://` ya `https://` wale links bhejiye.", 
                              "reply_to_message_id": message_id,
                              "parse_mode": "Markdown"
                          })
            return "ok", 200

        # 2. URL FILTER (Sirf link process hoga)
        if not (user_msg.startswith("http://") or user_msg.startswith("https://")):
            return "ok", 200

        # 3. Processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            nick_reply = loop.run_until_complete(get_final_reply(user_msg))
            
            # 4. As it is Forward (with reply)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={
                              "chat_id": chat_id, 
                              "text": nick_reply,
                              "reply_to_message_id": message_id
                          })
        except:
            pass # Vercel timeout handle karne ke liye

    return "ok", 200

@app.route('/')
def home():
    return "Bot is Running Perfectly!"
