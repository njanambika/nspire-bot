from flask import Flask, request
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    dummy = os.environ.get("DUMMY_VAR")
    verify = os.environ.get("VERIFY_TOKEN")
    return f"""✅ Env Test Successful!
    <br>DUMMY_VAR = {dummy or '❌ Not Found'}
    <br>VERIFY_TOKEN = {verify or '❌ Not Found'}
    """

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    verify_token = os.environ.get("VERIFY_TOKEN", "")

    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == verify_token:
            return challenge, 200
        else:
            return f"❌ Forbidden - Token mismatch (token={token}, expected={verify_token})", 403

    return "✅ Webhook received", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("✅ Starting app with these env variables:")
    print("DUMMY_VAR:", os.environ.get("DUMMY_VAR"))
    print("VERIFY_TOKEN:", os.environ.get("VERIFY_TOKEN"))
    app.run(host="0.0.0.0", port=port)
