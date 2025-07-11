from flask import Flask, request
import os
import re
import requests
from openai import OpenAI

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "").strip()
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=OPENAI_API_KEY)

raw_id = os.environ.get("PHONE_NUMBER_ID", "").strip()
PHONE_NUMBER_ID = re.sub(r"\D", "", raw_id).zfill(15)[:15]

session_data = {}
abuse_tracker = {}

@app.route("/", methods=["GET"])
def home():
    return "✅ Njanambika Tech Spire Bot is running!"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        return (challenge, 200) if mode == "subscribe" and token == VERIFY_TOKEN else ("Forbidden", 403)

    if request.method == "POST":
        data = request.get_json()
        print("📩 Incoming:", data)

        if data.get("object") == "whatsapp_business_account":
            for entry in data["entry"]:
                for change in entry["changes"]:
                    value = change["value"]
                    messages = value.get("messages", [])
                    for message in messages:
                        from_number = message["from"]
                        message_text = message.get("text", {}).get("body", "").strip()
                        message_type = message.get("type", "")

                        if message_type == "audio":
                            send_whatsapp_message(from_number, "🎧 Voice messages are not supported. Kindly type your message.")
                            return "OK", 200

                        if is_abusive(message_text):
                            abuse_tracker[from_number] = abuse_tracker.get(from_number, 0) + 1
                            send_whatsapp_message(from_number, "⚠️ Please be respectful. We’re here to help.")
                            return "OK", 200

                        response = intelligent_flow(from_number, message_text)
                        send_whatsapp_message(from_number, response)
        return "OK", 200

def intelligent_flow(user_id, message_text):
    user = session_data.get(user_id, {"step": 1})

    # --- Session close (polite) ---
    if message_text.strip().lower() in ["yes", "yeah", "ok", "close", "close session", "end", "end session"]:
        session_data.pop(user_id, None)
        return "Thank you for chatting with us! Your session is now closed. If you need anything else, just say hi."

    # --- "No more" detection: ask if want to close
    if message_text.strip().lower() in ["no", "nothing else", "that’s all", "no more", "all clear"]:
        session_data[user_id] = {"step": 100, "just_asked_to_close": True}
        return "Can I close this session now?"

    if user.get("just_asked_to_close"):
        session_data.pop(user_id, None)
        return "Thank you for chatting with us! Your session is now closed. If you need anything else, just say hi."

    # --- Main flow ---
    # Step 1: Name
    if user["step"] == 1:
        user["name"] = message_text
        user["step"] = 2
        session_data[user_id] = user
        return f"Nice to meet you, {user['name']}! 😊\nIs this application for yourself or someone else?"

    # Step 2: Self or other
    if user["step"] == 2:
        if message_text.strip().lower() in ["me", "myself", "self", "mine"]:
            user["for_whom"] = "self"
            user["step"] = 3
            session_data[user_id] = user
            return "Great! Which service do you need help with? (e.g., income certificate, caste certificate)"
        else:
            user["for_whom"] = "other"
            user["step"] = 2.5
            session_data[user_id] = user
            return "May I know their name?"

    # Step 2.5: If for someone else, get their name
    if user["step"] == 2.5:
        user["other_name"] = message_text
        user["step"] = 3
        session_data[user_id] = user
        return f"Which service does {user['other_name']} need help with?"

    # Step 3: Get service/need and use GPT-4 for next step
    if user["step"] == 3:
        user["service"] = message_text
        user["step"] = 4
        session_data[user_id] = user

        # Intelligent check: Should we ask what documents user already has?
        if should_ask_documents(user["service"]):
            user["awaiting_documents"] = True
            session_data[user_id] = user
            # The question is gentle and "only if needed"
            return ("For some services, certain certificates or documents are needed. "
                    "Would you like to share what documents or certificates you already have for this? If not sure, just say 'not sure'.")
        else:
            # Go straight to GPT reply (skip document question)
            return generate_persona_response(user)

    # Step 4: Get user's available documents/certificates (if relevant)
    if user.get("awaiting_documents"):
        user["user_documents"] = message_text
        user.pop("awaiting_documents")
        session_data[user_id] = user
        return generate_persona_response(user)

    # If reached here, fallback (reset session)
    session_data[user_id] = {"step": 1}
    return "👋 Hello! May I know your name?"

def should_ask_documents(service_text):
    """
    Intelligent check if it's necessary to ask user about existing documents.
    Only ask for common document-based services, not for everything.
    """
    keywords = ["certificate", "id", "card", "proof", "ration", "birth", "income", "caste", "license", "registration", "passport"]
    text = service_text.lower()
    return any(kw in text for kw in keywords)

def generate_persona_response(user):
    try:
        name = user.get('name', '')
        service = user.get('service', '')
        for_whom = user.get('other_name', '') if user.get('for_whom') == "other" else name
        user_docs = user.get('user_documents', '')

        prompt = (
            "You are a friendly, helpful assistant at Njanambika Tech Spire, a government citizen service centre. "
            "ONLY answer questions related to government, citizen services, official certificates, applications, and centre support. "
            "If the user's question is about movies, food, sports, or any other topic, politely say: "
            "'I’m here to assist with government and citizen services only. Please ask about official certificates or services.' "
            "Do NOT answer questions outside citizen services. "
            "Always keep replies under 60 words, use clear, simple language. "
            "Never explain how to apply online. Only mention who is eligible, what documents are needed, "
            "and always close with: 'Please visit our centre — we’ll help you with everything.' "
            "If the user has said which documents they already have, take that into account and give the most relevant suggestion. "
            "Here are the details:\n"
            f"- Name: {for_whom}\n"
            f"- Service: {service}\n"
            f"- Documents user says they have: {user_docs}\n"
            "If the user needs something else, answer naturally."
        )

        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=100,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ GPT Error:", e)
        return "Thanks for your details. Our team will help you shortly."

def is_abusive(text):
    return any(word in text.lower() for word in ["idiot", "stupid", "waste", "xxx", "sex"])

def send_whatsapp_message(to_number, text):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(url, headers=headers, json=payload)
    print("📤 Reply sent:", response.status_code, response.text)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
