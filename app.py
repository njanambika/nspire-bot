from flask import Flask, request
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    dummy = os.environ.get("DUMMY_VAR", "Variable not found")
    return f"✅ Env Test Successful! DUMMY_VAR = {dummy}"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "❌ Forbidden - Token mismatch", 403
    return "✅ Webhook received", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
