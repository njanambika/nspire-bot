from flask import Flask, request
import os
import re
import requests
from openai import OpenAI

app = Flask(__name__)

# ENV VARS
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "").strip()
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=OPENAI_API_KEY)

# Format and validate 15-digit phone number ID
raw_id = os.environ.get("PHONE_NUMBER_ID", "").strip()
PHONE_NUMBER_ID = re.sub(r"\D", "", raw_id).zfill(15)[:15]

# Session memory
abuse_tracker = {}
session_data = {}

@app.route("/", methods=["GET"])
def home():
    return "✅ Njanambika Tech Spire Bot is running!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        return (challenge, 200) if mode == "subscribe" and token == VERIFY_TOKEN else ("Forbidden", 403)

    if request.method == "POST":
        data = request.get_json()
        print("📩 Incoming:", data)

        if data.get("object") == "whatsapp_business_account":
            for entry in data["entry"]:
                for change in entry["changes"]:
                    value = change["value"]
                    messages = value.get("messages", [])
                    for message in messages:
                        from_number = message["from"]
                        message_text = message.get("text", {}).get("body", "").strip()
                        message_type = message.get("type", "")

                        if message_type == "audio":
                            send_whatsapp_message(from_number, "🎧 Voice messages are not supported. Kindly type your message.")
                            return "OK", 200

                        if is_abusive(message_text):
                            abuse_tracker[from_number] = abuse_tracker.get(from_number, 0) + 1
                            send_whatsapp_message(from_number, "⚠️ Please be respectful. We’re here to help.")
                            return "OK", 200

                        response = handle_persona_flow(from_number, message_text)
                        send_whatsapp_message(from_number, response)
        return "OK", 200

def handle_persona_flow(user_id, message_text):
    user = session_data.get(user_id, {"step": 1})

    if user["step"] == 1:
        name = message_text if message_text.lower() not in ["hi", "hello", "hey"] else "there"
        user["name"] = name
        session_data[user_id] = {**user, "step": 2}
        return f"Nice to meet you, {name}! 😊\nIs this application for *yourself* or *someone else*?"

    if user["step"] == 2:
        user["for_whom"] = message_text
        session_data[user_id] = {**user, "step": 3}
        return "Great! Which service do you need help with? (e.g., income certificate, caste certificate)"

    if user["step"] == 3:
        user["service"] = message_text
        session_data[user_id] = {**user, "step": 4}
        return generate_persona_response(user)

    session_data[user_id] = {"step": 1}
    return "👋 Hello! May I know your name?"

def generate_persona_response(user):
    try:
        prompt = (
            f"You are a warm and helpful assistant for Njanambika Tech Spire. "
            f"Make your response feel personal and friendly. The person’s name is {user['name']}, "
            f"applying for {user['service']} for {user['for_whom']}. "
            "Reply with a human-style summary that includes:\n\n"
            "🆔 Service\n"
            "🨾 Eligibility\n"
            "📁 Required Documents\n"
            "📆 Last Date (only if it’s genuinely required)\n"
            "📍 Close with: 'Kindly visit our centre — we’ll help you complete it confidently.'\n\n"
            "Skip robotic phrases like 'Dear'. Sound natural, warm, and concise."
        )
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=250,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ GPT Error:", e)
        return "Thanks for your details. Our team will help you shortly."

def is_abusive(text):
    return any(word in text.lower() for word in ["idiot", "stupid", "waste", "xxx", "sex"])

def send_whatsapp_message(to_number, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=payload)
    print("📤 Reply sent:", response.status_code, response.text)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
