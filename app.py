from flask import Flask, request
import os
import requests
import json

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.environ.get("PERMANENT_TOKEN")
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

    elif request.method == "POST":
        data = request.get_json()
        print("📩 Incoming Webhook Payload:", json.dumps(data, indent=2))

        # Extract sender info
        try:
            phone_number = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
            send_auto_reply(phone_number)
        except Exception as e:
            print("❌ Error extracting message or sending reply:", e)

        return "EVENT_RECEIVED", 200

    return "Method not allowed", 405

def send_auto_reply(recipient_number):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_number,
        "type": "text",
        "text": {
            "body": "Thanks for messaging, will be replied shortly."
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    print("📤 Auto-reply sent. Response:", response.status_code, response.text)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
