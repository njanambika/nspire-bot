from flask import Flask, request
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    dummy = os.environ.get("DUMMY_VAR", "Variable not found")
    return f"✅ Env Test Successful! DUMMY_VAR = {dummy}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
