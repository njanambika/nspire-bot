from flask import Flask, request
import os
import re
import requests
from openai import OpenAI

app = Flask(__name__)

# Load environment variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "").strip()
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

client = OpenAI(api_key=OPENAI_API_KEY)

# Clean phone number ID
raw_id = os.environ.get("PHONE_NUMBER_ID", "").strip()
clean_id = re.sub(r"\D", "", raw_id)
PHONE_NUMBER_ID = clean_id.zfill(15)[:15]

# Abuse tracker (simple memory-based)
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
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403

    if request.method == "POST":
        data = request.get_json()
        print("📩 Incoming Webhook Payload:", data)

        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for message in messages:
                        from_number = message["from"]
                        message_type = message.get("type", "")
                        message_text = message.get("text", {}).get("body", "").strip()

                        # 🎙️ Handle voice note
                        if message_type == "audio":
                            send_whatsapp_message(from_number, "🎙️ Voice messages are not supported. Kindly type your query so we can assist you better.")
                            return "OK", 200

                        # 🧠 Step 1: Detect intent
                        intent = classify_intent(message_text)

                        # 🛑 Handle abusive input — warn only
                        if intent == "abuse":
                            abuse_tracker[from_number] = abuse_tracker.get(from_number, 0) + 1
                            send_whatsapp_message(
                                from_number,
                                "⚠️ Let's keep this respectful. We're here to assist you with official citizen services."
                            )
                            return "OK", 200

                        # 🧽 Handle off-topic input
                        if intent == "irrelevant":
                            send_whatsapp_message(
                                from_number,
                                "🙏 This assistant is here to help with Akshaya-related citizen services. Kindly ask about certificates, applications, or related support."
                            )
                            return "OK", 200

                        # ✅ Valid service intent
                        if is_apply_intent(message_text):
                            reply = "✅ This service is available. Please visit our centre for professional assistance."
                        else:
                            reply = generate_openai_reply(message_text)

                        send_whatsapp_message(from_number, reply)

        return "OK", 200

# 🔍 GPT-based intent classifier
def classify_intent(user_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a classifier for a citizen service chatbot in Kerala. "
                        "Classify the user's message into one of three categories:\n"
                        "- 'akshaya_service': if it's about certificates, documents, ID cards, applications, or citizen schemes\n"
                        "- 'irrelevant': if it's about jokes, food, weather, movies, general chatting\n"
                        "- 'abuse': if it contains rude, mocking, offensive, or spammy words\n"
                        "Respond with only one word: akshaya_service, irrelevant, or abuse"
                    )
                },
                {"role": "user", "content": f"Message: {user_text}"}
            ],
            max_tokens=5,
            temperature=0
        )
        intent = response.choices[0].message.content.strip().lower()
        print("🧠 Detected Intent:", intent)
        return intent
    except Exception as e:
        print("⚠️ Intent classification failed:", e)
        return "irrelevant"

# ✅ Detect apply-related messages
def is_apply_intent(text):
    keywords = [
        "apply", "certificate", "upload", "how to", "form", "cheyyanam",
        "varumana", "submit", "register", "income", "birth", "online"
    ]
    return any(word.lower() in text.lower() for word in keywords)

# 🤖 GPT-generated clarifications (no how-to)
def generate_openai_reply(user_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional assistant for Njanambika Tech Spire, working with Akshaya CSC centres. "
                        "Your job is to politely clarify the purpose of certificates or services. "
                        "NEVER explain how to apply, upload, or complete online steps. "
                        "If asked, reply: 'Please visit our centre for complete support.' "
                        "Maintain a respectful, natural tone. Be short, polite, and helpful."
                    )
                },
                {"role": "user", "content": user_text}
            ],
            max_tokens=150,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ OpenAI Error:", e)
        return "Sorry, I’m unable to respond right now. Please try again later."

# 📤 WhatsApp reply
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
    print("📤 WhatsApp reply sent:", response.status_code, response.text)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
