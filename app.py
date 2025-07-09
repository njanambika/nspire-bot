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
                        
                        # ❌ Voice note check
                        if message_type == "audio":
                            send_whatsapp_message(from_number, "🎙️ Voice messages not supported. Kindly type your query.")
                            return "OK", 200
                        
                        # 📝 Text check
                        message_text = message.get("text", {}).get("body", "").strip()

                        # 🚫 Block irrelevant/abusive input
                        if is_irrelevant_or_abusive(message_text):
                            send_whatsapp_message(from_number, "🙏 I’m here to help with citizen services. Please ask about a service or certificate.")
                            return "OK", 200

                        # 🔍 Check intent
                        if is_apply_intent(message_text):
                            reply = "✅ This service is available. Please visit our centre for full support and professional assistance."
                        else:
                            # 🧠 Use GPT only for valid clarification
                            reply = generate_openai_reply(message_text)

                        send_whatsapp_message(from_number, reply)

        return "OK", 200


# 🔍 Keyword intent detector
def is_apply_intent(text):
    keywords = ["apply", "income", "birth", "certificate", "upload", "cheyyanam", "varumana", "epass", "how to", "form"]
    return any(word.lower() in text.lower() for word in keywords)


# 🚫 Irrelevant / abusive check
def is_irrelevant_or_abusive(text):
    banned = ["who is pm", "joke", "weather", "sex", "xxx", "stupid", "idiot", "modi", "pinarayi", "politics"]
    return any(b in text.lower() for b in banned)


# 🧠 GPT to clarify only, not guide
def generate_openai_reply(user_text):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for Njanambika Tech Spire in partnership with Akshaya CSC centres. "
                        "Only clarify what a certificate or process means. Do NOT explain how to apply or do online steps. "
                        "If asked for 'how', just say 'Please visit our centre for full support.' "
                        "Be natural, respectful, and keep replies short and local-friendly."
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


# 📤 WhatsApp reply sender
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
