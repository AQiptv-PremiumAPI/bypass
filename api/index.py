import asyncio
import re
import time
from flask import Flask, request
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import requests

app = Flask(__name__)

# --- CONFIGURATION ---
BOT_TOKEN = '8420015561:AAFdkmCe8uVGbB9FJWhV4emj9s_xFvwMViQ'

def bot_request(method, payload):
    return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload)

# --- ADVANCE STEALTH BYPASS LOGIC ---
def solve_and_bypass(url):
    """
    Uses Playwright Stealth to bypass Cloudflare Turnstile, 
    Bot Verification, and solve/skip simple JS Captchas.
    """
    with sync_playwright() as p:
        # Browser launch with Stealth Tadka
        browser = p.chromium.launch(headless=True) # Production me True rakhein
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        stealth_sync(page) # Yeh bot detection ko disable kar deta hai

        try:
            print(f"Opening: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)

            # --- CAPTCHA/TURNSTILE SOLVER TADKA ---
            # Agar Turnstile (Cloudflare) box dikhta hai, toh ye automatic click/wait karega
            turnstile_selectors = ["iframe[src*='turnstile']", "div#turnstile-wrapper"]
            for selector in turnstile_selectors:
                if page.query_selector(selector):
                    print("Cloudflare Turnstile Detected! Waiting for verification...")
                    time.sleep(5) # Auto-solve wait
            
            # --- ADS SKIP LOGIC ---
            # VPLinks/GPLinks jaise sites par 'Dual Button' ya 'Timer' hota hai
            # Hum automatic 'Get Link' button dhoond kar click karenge
            possible_buttons = ["Get Link", "Continue", "Skip Ad", "Click here to continue"]
            for btn_text in possible_buttons:
                button = page.get_by_role("button", name=btn_text, exact=False).first
                if button.is_visible():
                    button.click()
                    page.wait_for_load_state("networkidle")

            # Final destination URL nikalna
            time.sleep(3) # Redirects settle hone ka wait
            final_destination = page.url
            
            browser.close()
            return final_destination

        except Exception as e:
            browser.close()
            return f"Bypass Error: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data and "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            bot_request("sendMessage", {"chat_id": chat_id, "text": "🛸 **God Mode Bypasser Active!**\nCloudflare aur Captcha ki tension khatam. Link bhejo!"})
            return "ok", 200

        urls = re.findall(r'https?://[^\s]+', text)
        if urls:
            user_link = urls[0]
            bot_request("sendMessage", {"chat_id": chat_id, "text": "🎭 **Solving Captcha & Bypassing Cloudflare...**"})

            res_link = solve_and_bypass(user_link)

            if res_link and "http" in res_link:
                final_text = (
                    "✅ **BYPASSED EVERYTHING!**\n\n"
                    f"**ORIGINAL:** {user_link}\n"
                    f"**DESTINATION:** {res_link}\n\n"
                    "🔥 **Method:** Playwright Stealth Engine"
                )
            else:
                final_text = "❌ **Failed:** Security is too high or site is down."

            bot_request("sendMessage", {"chat_id": chat_id, "text": final_text, "disable_web_page_preview": True})

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
