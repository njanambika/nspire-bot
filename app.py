from flask import Flask, request
import os
import re
import requests
from openai import OpenAI

app = Flask(__name__)

# --- ENVIRONMENT VARIABLES ---
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "").strip()
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=OPENAI_API_KEY)
raw_id = os.environ.get("PHONE_NUMBER_ID", "").strip()
PHONE_NUMBER_ID = re.sub(r"\D", "", raw_id).zfill(15)[:15]

# --- SESSION STORAGE ---
session_data = {}

@app.route("/", methods=["GET"])
def home():
    return "✅ Njanambika Tech Spire Bot (Violet) is running!"

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
                            send_whatsapp_message(from_number, "⚠️ Please be respectful. We’re here to help.")
                            return "OK", 200

                        response = handle_conversation(from_number, message_text)
                        send_whatsapp_message(from_number, response)
        return "OK", 200

def handle_conversation(user_id, message_text):
    # --- User session retrieval ---
    user = session_data.get(user_id, None)

    # --- New or Reset Session ---
    if user is None:
        session_data[user_id] = {
            "step": "awaiting_name",
            "history": [],
            "asked_to_close": False
        }
        return "Hello! I’m Violet, your assistant from Njanambika Tech Spire. 😊 May I know your name?"

    # --- Session close logic ---
    close_words = ["yes", "close", "end", "ok", "close session", "end session"]
    if message_text.strip().lower() in close_words:
        if user.get("asked_to_close"):
            session_data.pop(user_id, None)
            return "Thank you for chatting with us! Your session is now closed. If you need anything else, just say hi."

    if message_text.strip().lower() in ["no", "nothing else", "that's all", "no more", "all clear"]:
        user["asked_to_close"] = True
        session_data[user_id] = user
        return "Can I close this session now?"

    # --- State Machine Logic ---
    step = user["step"]

    if step == "awaiting_name":
        # Accept any non-blank input as the name
        name = message_text.strip()
        if not name or len(name) > 32 or name.lower() in ["hi", "hello"]:
            return "Could you please tell me your name to proceed?"
        user["name"] = name
        user["step"] = "awaiting_for_whom"
        session_data[user_id] = user
        return f"Nice to meet you, {user['name']}! 😊 Is this application for yourself or someone else?"

    if step == "awaiting_for_whom":
        # Accept self/other
        if message_text.strip().lower() in ["myself", "me", "self"]:
            user["for_whom"] = "myself"
            user["step"] = "awaiting_service"
            session_data[user_id] = user
            return "Great! What service do you need help with?"
        else:
            user["for_whom"] = "someone else"
            user["step"] = "awaiting_target_name"
            session_data[user_id] = user
            return "May I know their name?"

    if step == "awaiting_target_name":
        target_name = message_text.strip()
        if not target_name or len(target_name) > 32:
            return "Please provide a valid name."
        user["target_name"] = target_name
        user["step"] = "awaiting_service"
        session_data[user_id] = user
        return f"Which service does {user['target_name']} need help with?"

    if step == "awaiting_service":
        user["service"] = message_text.strip()
        user["step"] = "in_chat"
        # Compose system prompt for OpenAI
        system_prompt = (
            "You are Violet, a friendly, helpful assistant at Njanambika Tech Spire, a government citizen service centre. "
            "ONLY answer questions related to government, citizen services, official certificates, applications, and centre support. "
            "If the user's question is about movies, food, sports, or any other topic, politely say: "
            "'I’m here to assist with government and citizen services only. Please ask about official certificates or services.' "
            "Do NOT answer questions outside citizen services. "
            "Always keep replies under 60 words, use clear, simple language. "
            "Never explain how to apply online. Only mention who is eligible, what documents are needed, "
            "and always close with: 'Please visit our centre — we’ll help you with everything.' "
            "Remember everything the user has asked earlier in this chat and answer follow-up questions accordingly."
        )
        history = [{"role": "system", "content": system_prompt}]
        # Context
        context = f"Name: {user['name']}, For: {user.get('target_name', user['for_whom'])}, Service: {user['service']}"
        history.append({"role": "user", "content": context})
        user["history"] = history
        session_data[user_id] = user
        reply = generate_persona_response(user["history"])
        user["history"].append({"role": "assistant", "content": reply})
        session_data[user_id] = user
        return reply

    if step == "in_chat":
        # GPT-style memory and full assistant power!
        user["history"].append({"role": "user", "content": message_text})
        reply = generate_persona_response(user["history"])
        user["history"].append({"role": "assistant", "content": reply})
        session_data[user_id] = user
        return reply

    # --- Fallback (should never be reached) ---
    session_data.pop(user_id, None)
    return "Sorry, something went wrong. Let's start again. What is your name?"

def generate_persona_response(history):
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=history,
            max_tokens=120,
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
