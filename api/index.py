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
# Aapka String Session
STRING_SESSION = "1BVtsOIMBuxpEfQxpdroVzE6VZ3Z7ZXSgZU5C3rCDrmwMpnHDnMdZdHLQF80003Ysr1AvMkSy5dlle0OO7RZTLQIQnEza9XasCzpv8rrhYcaf0QGyIKf_COX-GKdedv_4XXFLlbyufhZAfeVjJyZNCG9VP0ex_fh9uek-R9ExQn7qxfbBbr0ONLYcV-32qX68ljBYclI8QiqIutqNvlSP9vnEdqEoD-Uhfe7XdVukMc8bKJNG4kWl6E7BjOOtuZHpvfShDMXFaZCTcq8mw1ela4UzSNxfTnk-GT_tZTH288X_TZUGtVvPUsdWrKkTEUhHclgn_F7HrNwxzCVylTCw47C5XDVEbnA=" 
TARGET_BOT = "@nick_bypass_bot"

async def get_final_reply(user_msg):
    # Aapki ID se login karna (StringSession)
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    final_text = ""
    try:
        async with client.conversation(TARGET_BOT, timeout=45) as conv:
            # Nick bot ko message bhejna
            await conv.send_message(user_msg)
            
            # Pehla response pakadna (Processing...)
            response = await conv.get_response()
            final_text = response.text
            
            # Dusra response pakadna (Asli Bypass Link)
            try:
                # 15 second tak wait karega asli link ke liye
                response = await conv.get_response(timeout=15)
                final_text = response.text
            except:
                # Agar dusra message nahi aaya toh pehla wala hi rakhega
                pass

            # --- BRANDING REMOVAL LOGIC ---
            if final_text:
                # Purane naam ko naye naam se replace karna
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
        chat_id = data["message"]["chat"]["id"]
        user_msg = data["message"]["text"]

        # Start Command Handling
        if user_msg == "/start":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "✅ *Bot Active!*\n\nLink bhejiye, main usse bypass karke deta hoon.", "parse_mode": "Markdown"})
            return "ok", 200

        # Nick Bot se link nikalne ka process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Nick bot se reply lena aur edit karna
            nick_reply = loop.run_until_complete(get_final_reply(user_msg))
            
            # User ko modified reply bhejna
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": nick_reply})
        except:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "❌ Nick Bot ne respond nahi kiya. Thodi der baad try karein."})

    return "ok", 200

@app.route('/')
def home():
    return "Bot is Running with Branding Replacement!"
            
