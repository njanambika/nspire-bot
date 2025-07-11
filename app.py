from flask import Flask, request
import os
import re
import requests
from openai import OpenAI

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "").strip()
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=OPENAI_API_KEY)

raw_id = os.environ.get("PHONE_NUMBER_ID", "").strip()
PHONE_NUMBER_ID = re.sub(r"\D", "", raw_id).zfill(15)[:15]

session_data = {}
abuse_tracker = {}

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

                        response = handle_conversation_memory(from_number, message_text)
                        send_whatsapp_message(from_number, response)
        return "OK", 200

def handle_conversation_memory(user_id, message_text):
    # --- New: Check if user wants to close session
    if message_text.strip().lower() in ["yes", "yeah", "ok", "close", "close session", "end", "end session"]:
        session_data.pop(user_id, None)
        return "Thank you for chatting with us! Your session is now closed. If you need anything else, just say hi."

    # Retrieve or initialize the user's conversation history
    history = session_data.get(user_id, {}).get("history", [])

    # Add system prompt if starting a new conversation
    if not history:
        system_prompt = (
            "You are a friendly, helpful assistant at Njanambika Tech Spire, a common service centre. "
            "Always keep replies under 60 words, use clear, simple language. "
            "Never explain how to apply online. Only mention who is eligible, what documents are needed, "
            "and always close with: 'Please visit our centre — we’ll help you with everything.' "
            "Remember everything the user has asked earlier in this chat and answer follow-up questions accordingly."
        )
        history.append({"role": "system", "content": system_prompt})

    # Add user message to history
    history.append({"role": "user", "content": message_text})

    # Get AI reply (passing full conversation history)
    reply = generate_persona_response(history)
    reply += "\n\nIf you don’t have any more questions, can I close this session?"  # <--- NEW

    history.append({"role": "assistant", "content": reply})

    # Save back to session_data
    session_data[user_id] = {"history": history}

    return reply

def generate_persona_response(history):
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=history,
            max_tokens=100,
            temperature=0.4
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
