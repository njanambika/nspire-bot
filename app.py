from flask import Flask, request
import os
import requests
import json

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")  # Required to reply
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")  # From Meta WhatsApp dashboard

@app.route("/", methods=["GET"])
def home():
    return "✅ Nspire Bot is running!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Verification with Meta
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Forbidden", 403

    if request.method == "POST":
        data = request.get_json()
        print("📥 Incoming webhook:", json.dumps(data, indent=2))

        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    if messages:
                        message = messages[0]
                        from_number = message["from"]
                        text = message["text"]["body"]
                        print(f"💬 Message from {from_number}: {text}")

                        # Optional: Send reply
                        send_whatsapp_reply(from_number, "Thanks for your message!")

        return "EVENT_RECEIVED", 200

    return "Not allowed", 405


def send_whatsapp_reply(recipient_id, message_text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_id,
        "type": "text",
        "text": {"body": message_text}
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"📤 Sent reply: {response.status_code} - {response.text}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
