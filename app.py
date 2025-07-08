from flask import Flask, request
import os

app = Flask(__name__)

# Get the VERIFY_TOKEN from environment variable
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

@app.route("/", methods=["GET"])
def home():
    return "✅ Nspire Bot is running!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        # Extract query parameters from Facebook
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        print(f"🔍 Mode: {mode}, Token: {token}, Challenge: {challenge}")

        # Check token match
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "❌ Forbidden - Token mismatch", 403

    # Optional: Log POST request (incoming messages)
    if request.method == "POST":
        print("📩 Received POST:", request.json)
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
