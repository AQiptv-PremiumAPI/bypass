from flask import Flask, request
from telethon import TelegramClient
import asyncio
import requests

app = Flask(__name__)

# Details jo aapne di hain
API_ID = 39707299 
API_HASH = 'd6d90ebfeb588397f9229ac3be55cfdf'
BOT_TOKEN = '8374143251:AAGY5_QfDcr_PZ2b2zAoD8WMbXr1Hubm-jw'
TARGET_BOT = "@nick_bypass_bot" # Yahi format sahi hai

async def get_nick_reply(user_msg):
    # None session matlab memory mein session banega, file save nahi hogi (Vercel ke liye best)
    client = TelegramClient(None, API_ID, API_HASH) 
    await client.start(bot_token=BOT_TOKEN)
    
    try:
        # Nick bot se baat shuru karna
        async with client.conversation(TARGET_BOT, timeout=20) as conv:
            await conv.send_message(user_msg)
            response = await conv.get_response()
            return response.text
    except Exception as e:
        return f"⚠️ Nick Bot Slow Hai Ya Error Aaya: {str(e)}"
    finally:
        await client.disconnect()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        user_msg = data["message"]["text"]
        chat_id = data["message"]["chat"]["id"]

        # Fix: Variable name ko user_msg kar diya
        if user_msg == "/start":
             requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={chat_id}&text=Bhai, link bhejo bypass karne ke liye!")
             return "ok", 200

        # Typing action dikhana taaki user ko lage bot kaam kar raha hai
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

        # Async process chalana
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            nick_reply = loop.run_until_complete(get_nick_reply(user_msg))
            
            # User ko reply bhejna
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": nick_reply})
        except:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "Vercel ne process kill kar diya. Dobara try karein!"})
        
    return "ok", 200

@app.route('/')
def home():
    return "Bot is active!"
