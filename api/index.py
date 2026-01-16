from flask import Flask, request
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import requests

app = Flask(__name__)

# --- CONFIG ---
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
        async with client.conversation(TARGET_BOT, timeout=40) as conv:
            await conv.send_message(user_msg)
            
            # 1. Pehla message (e.g. "Processing...")
            response = await conv.get_response()
            final_text = response.text
            
            # 2. YAHAN JADU HAI: Hum 5-8 second wait karenge jab tak bot asli link na bhej de
            # Agar bot message edit karta hai ya naya bhejta hai toh ye usse pakad lega
            try:
                # Nick bot thoda time leta hai, isliye hum next message ka wait karenge
                response = await conv.get_response(timeout=15)
                final_text = response.text
            except:
                # Agar naya message nahi aaya, toh ho sakta hai purana wala hi final ho
                pass
                
    except Exception as e:
        final_text = f"Error: {str(e)}"
    finally:
        await client.disconnect()
    
    return final_text

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"]["text"]

        if user_msg == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "Bot Active! Link bhejiye, main Nick Bot se nikal kar deta hoon..."})
            return "ok", 200

        # Vercel ko reply dene ke liye pehle bata dete hain ki hum kaam kar rahe hain
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Final reply mangwana (Wait logic ke saath)
            nick_reply = loop.run_until_complete(get_final_reply(user_msg))
            
            # User ko asli result bhejna
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": nick_reply})
        except:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "Nick Bot ne reply dene mein zyada time le liya. Dubara try karein."})

    return "ok", 200

@app.route('/')
def home():
    return "Userbot Middleman is Active!"
