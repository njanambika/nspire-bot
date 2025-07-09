from flask import Flask, request
import os
import requests

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

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

                        # Send auto-reply
                        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
                        headers = {
                            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "messaging_product": "whatsapp",
                            "to": from_number,
                            "type": "text",
                            "text": { "body": "Thanks for messaging, will be replied shortly." }
                        }

                        response = requests.post(url, headers=headers, json=payload)
                        print("📤 Auto-reply sent. Response:", response.status_code, response.text)

        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
