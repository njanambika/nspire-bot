from flask import Flask, request
import os
import re
import requests
from openai import OpenAI

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "").strip()
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

client = OpenAI(api_key=OPENAI_API_KEY)

# Phone number ID cleanup
raw_id = os.environ.get("PHONE_NUMBER_ID", "").strip()
clean_id = re.sub(r"\D", "", raw_id)
PHONE_NUMBER_ID = clean_id.zfill(15)[:15]

# Abuse tracking (simple in-memory for demo)
abuse_tracker = {}

@app.route("/", methods=["GET"])
def home():
    return "✅ Nspire Bot is running!"


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
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

                        # 🎙️ Block voice messages
                        if message_type == "audio":
                            send_whatsapp_message(from_number, "🎙️ Voice messages not supported. Kindly type your query.")
                            return "OK", 200

                        # 🚫 Handle irrelevant or abusive input
                        if is_irrelevant(message_text):
                            send_whatsapp_message(from_number, "🙏 I’m here to assist with citizen services. Please ask about services or certificates.")
                            return "OK", 200

                        if is_abusive(message_text):
                            abuse_tracker[from_number] = abuse_tracker.get(from_number, 0) + 1
                            if abuse_tracker[from_number] >= 2:
                                send_whatsapp_message(from_number, "🚫 Conversation ended due to repeated offensive messages. Please contact staff.")
                                # Optionally: Notify staff
                                return "OK", 200
                            else:
                                send_whatsapp_message(from_number, "⚠️ Please be respectful. I’m here to help with services.")
                                return "OK", 200

                        # 📂 Handle document/image messages (future)
                        if message_type in ["image", "document"]:
                            send_whatsapp_message(from_number, "📁 Document received. Our team will check and assist you.")
                            return "OK", 200

                        # ✅ If service intent detected
                        if is_apply_intent(message_text):
                            reply = "✅ This service is available. Please visit our centre for professional support."
                        else:
                            reply = generate_openai_reply(message_text)

                        send_whatsapp_message(from_number, reply)

        return "OK", 200


# 🔍 Keyword intent detector
def is_apply_intent(text):
    keywords = ["apply", "certificate", "upload", "how to", "form", "cheyyanam", "varumana", "submit", "register", "income", "birth", "online"]
    return any(word.lower() in text.lower() for word in keywords)


# 🚫 Block irrelevant or joke topics
def is_irrelevant(text):
    irrelevant = ["joke", "weather", "song", "story", "who is pm", "movie", "modi", "pinarayi"]
    return any(word in text.lower() for word in irrelevant)


# 🛑 Detect abuse or political provocation
def is_abusive(text):
    abusive = ["idiot", "stupid", "fool", "waste", "bloody", "sex", "xxx", "fake", "nonsense", "politics", "bjp", "congress", "communist"]
    return any(word in text.lower() for word in abusive)


# 🧠 GPT – Clarify, never teach steps
def generate_openai_reply(user_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for Njanambika Tech Spire, working with Akshaya CSC centres. "
                        "Your job is to clarify citizen doubts in a human tone. "
                        "You can explain what a certificate means, or who might need it. "
                        "NEVER explain how to apply, where to upload, or give online steps. "
                        "For any such request, say: 'Please visit our centre for complete support.' "
                        "Be respectful, short, and encourage offline help."
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


# 📤 Send message to WhatsApp
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
