from flask import Flask, request
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    dummy = os.environ.get("DUMMY_VAR")
    verify = os.environ.get("VERIFY_TOKEN")

    # Print to Railway logs for debugging
    print("✅ ENV CHECK -- DUMMY_VAR:", dummy)
    print("✅ ENV CHECK -- VERIFY_TOKEN:", verify)

    return f"""
    ✅ Env Test Successful!<br>
    DUMMY_VAR = {"✅ " + dummy if dummy else "❌ Not Found"}<br>
    VERIFY_TOKEN = {"✅ " + verify if verify else "❌ Not Found"}
    """

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verified successfully.")
            return challenge, 200
        else:
            print("❌ Webhook verification failed.")
            return "Forbidden - Token mismatch", 403

    if request.method == "POST":
        print("✅ Webhook POST received.")
        return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
