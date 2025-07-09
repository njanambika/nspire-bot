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

# Set up OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Clean and format phone number ID
raw_id = os.environ.get("PHONE_NUMBER_ID", "").strip()
clean_id = re.sub(r"\D", "", raw_id)
PHONE_NUMBER_ID = clean_id.zfill(15)[:15]


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
                        message_text = message.get("text", {}).get("body", "")

                        # 🔐 Generate filtered reply
                        reply = generate_openai_reply(message_text)

                        # 📤 Send reply via WhatsApp
                        send_whatsapp_message(from_number, reply)

        return "OK", 200


def generate_openai_reply(user_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                                "You are a polite and knowledgeable assistant for a citizen service provider called Njanambika Tech Spire, "
                                "working with Akshaya CSC centres in Kerala. "
                                "Your job is to help users understand government services, but never teach them how to apply online or fill forms. "
                                "If the user asks for eligibility, document meaning, or basic doubts — explain clearly in natural language. "
                                "If they ask how to apply, upload, register, or do online steps — reply with: "
                                "'This service is available. Kindly visit our centre for full support.' "
                                "Avoid giving instructions, links, or step-by-step guides. Be helpful, brief, and build trust in centre assistance."
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
        return "Sorry, I’m unable to reply right now. Please try again later."


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
