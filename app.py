from flask import Flask, request
import os
import json

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Nspire Bot is running!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "default_token")

    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification failed", 403

    if request.method == "POST":
        data = request.get_json()
        print("📩 Incoming message:", json.dumps(data, indent=2))
        return "EVENT_RECEIVED", 200

    return "Invalid request", 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
