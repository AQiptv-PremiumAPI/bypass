import os
import telebot
from flask import Flask, request

# Config
TOKEN = os.getenv("BOT_TOKEN")  # @tybot ka token
MY_ID = "7844485105"                 # Aapki ID
NICK_BOT_USER = "@Nick_Bypass_Bot"       # Jis bot ko bhejna hai

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@bot.message_handler(func=lambda message: True)
def relay_message(message):
    # User ka message lekar use forward karna
    try:
        # Yeh line message ko forward karegi
        # Note: Aapko pehle @nickbot ko message karke start karna hoga
        bot.forward_message(MY_ID, message.chat.id, message.message_id)
        
        # Ek text notification ki message kisne bheja hai
        bot.send_message(MY_ID, f"Sent to relay from: {message.chat.id}")
    except Exception as e:
        print(f"Error: {e}")

@app.route('/')
def index():
    return "Bot is running", 200
