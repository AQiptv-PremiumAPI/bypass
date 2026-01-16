from flask import Flask, request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import requests

app = Flask(__name__)

# --- CONFIG ---
API_ID = 39707299 
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
BOT_TOKEN = '8374143251:AAGY5_QfDcr_PZ2b2zAoD8WMbXr1Hubm-jw'
# Yahan apni nikaali hui String Session dalein
STRING_SESSION = "PASTE_YOUR_STRING_SESSION_HERE" 
TARGET_BOT = "@nick_bypass_bot"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"]["text"]

        if user_msg == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "Bot Active! Link bhejo..."})
            return "ok", 200

        # Nick Bot se baat karne wala logic
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def get_reply():
            # User client (Aapki ID)
            user_client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
            await user_client.start()
            
            async with user_client.conversation(TARGET_BOT, timeout=25) as conv:
                await conv.send_message(user_msg)
                response = await conv.get_response()
                reply_text = response.text
            
            await user_client.disconnect()
            return reply_text

        try:
            nick_reply = loop.run_until_complete(get_reply())
            # Result ko wapas user ko bhejna
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": nick_reply})
        except Exception as e:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": f"Error: {str(e)}"})

    return "ok", 200

@app.route('/')
def home():
    return "Userbot is Active on Vercel!"
