from flask import Flask
import os

app = Flask(__name__)

# Load environment variable (make sure you set this in Railway under "Variables")
DUMMY_VAR = os.environ.get("DUMMY_VAR", "Variable not found")

@app.route("/")
def home():
    return f"✅ Env Test Successful! DUMMY_VAR = {DUMMY_VAR}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway sets this automatically
    app.run(host="0.0.0.0", port=port)
