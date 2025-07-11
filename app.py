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

# -------------------- LANGUAGE & INTENT DETECTION --------------------

def detect_language(message):
    # Malayalam Unicode
    for c in message:
        if '\u0d00' <= c <= '\u0d7f':
            return "ml"
    manglish_words = [
        "entha", "poyi", "kollam", "und", "njan", "alle", "vannu",
        "kaanaan", "evide", "onn", "chetta", "aadyam", "police", "chaya",
        "chumma", "poda", "poyi", "pattu", "kuttan", "nanayi", "sherikkum"
    ]
    msg_lower = message.lower()
    if any(word in msg_lower for word in manglish_words):
        return "manglish"
    return "en"

def get_greeting(language):
    return {
        "ml": "ഹലോ! ഞാൻ വൈലറ്റ് ആണ്, ജ്ഞാനാംബിക ടെക്ക് സ്പയറിൽ നിന്നുള്ള അസിസ്റ്റന്റ്. നിങ്ങളുടെ പേര് പറയാമോ?",
        "manglish": "Halo! Njan Violet aanu, Jnanambika Tech Spire il ninnulla assistant. Ningalude peru parayamo?",
        "en": "Hello! I’m Violet, your assistant from Jnanambika Tech Spire. 😊 May I know your name?"
    }[language]

def get_system_prompt(language):
    if language == "ml":
        return (
            "നിങ്ങൾ വൈലറ്റ് ആണ്, ജ്ഞാനാംബിക ടെക്ക് സ്പയറിലെ സൗഹൃദപരമായ സഹായിയാണ്. "
            "നീങ്ങളുടെ ഉത്തരം മലയാളത്തിൽ മാത്രം നൽകുക. "
            "സർവീസ് സംബന്ധിച്ച ചോദ്യങ്ങൾക്കും ഉത്തരങ്ങൾക്കും മാത്രം സഹായിക്കുക. "
            "ഉത്തരം വളരെ കുറച്ച് വാക്കുകളിൽ നൽകുക. ഓൺലൈനായി ചെയ്യുന്നത് വിശദമായി പറയരുത്. "
            "അവസാനം: 'ദയവായി ഞങ്ങളുടെ കേന്ദ്രം സന്ദർശിക്കുക — എല്ലാം സഹായിക്കാം' എന്ന് പറയുക."
        )
    elif language == "manglish":
        return (
            "നിങ്ങൾ വൈലറ്റ് ആണ്, ജ്ഞാനാംബിക ടെക്ക് സ്പയറിലെ സൗഹൃദപരമായ സഹായിയാണ്. "
            "മറുപടി മലയാളം ലിപിയിൽ മാത്രം നൽകുക, ഉപയോക്താവ് മംഗ്ലിഷ് ഉപയോഗിച്ചാലും. "
            "സർവീസ് സംബന്ധിച്ച ചോദ്യങ്ങൾക്കും ഉത്തരങ്ങൾക്കും മാത്രം സഹായിക്കുക. "
            "ഉത്തരം വളരെ കുറച്ച് വാക്കുകളിൽ നൽകുക. ഓൺലൈനായി ചെയ്യുന്നത് വിശദമായി പറയരുത്. "
            "അവസാനം: 'ദയവായി ഞങ്ങളുടെ കേന്ദ്രം സന്ദർശിക്കുക — എല്ലാം സഹായിക്കാം' എന്ന് പറയുക."
        )
    else:
        return (
            "You are Violet, a friendly assistant at Jnanambika Tech Spire, a government citizen service centre. "
            "ONLY answer questions related to government, citizen services, official certificates, applications, and centre support. "
            "If the user's question is about movies, food, sports, or any other topic, politely say: "
            "'I’m here to assist with government and citizen services only. Please ask about official certificates or services.' "
            "Do NOT answer questions outside citizen services. "
            "Always keep replies under 60 words, use clear, simple language. "
            "Never explain how to apply online. Only mention who is eligible, what documents are needed, "
            "and always close with: 'Please visit our centre — we’ll help you with everything.'"
        )

def extract_intent(history):
    try:
        intent_prompt = (
            "You are a government service assistant at Jnanambika Tech Spire. "
            "Given the conversation so far, extract what government service or certificate the user wants (like passport, Aadhaar, income certificate, KSEB, correction, duplicate, etc). "
            "Reply ONLY with the main intent/service name (like: aadhaar, kseb, pan card, income certificate, correction, new connection, etc). "
            "If not clear, reply: 'unknown'."
        )
        intent_history = [{"role": "system", "content": intent_prompt}]
        intent_history.extend(history)
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=intent_history,
            max_tokens=16,
            temperature=0
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        print("Intent error:", e)
        return "unknown"

# -------------------- FLASK BOT --------------------

@app.route("/", methods=["GET"])
def home():
    return "✅ Jnanambika Tech Spire Bot is running!"

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

                        response = handle_conversation(from_number, message_text)
                        send_whatsapp_message(from_number, response)
        return "OK", 200

# -------------------- BOT LOGIC & SESSION MACHINE --------------------

def handle_conversation(user_id, message_text):
    user = session_data.get(user_id, None)
    close_cmds = ["yes", "close", "end", "ok", "close session", "end session", "yes please", "exit"]
    no_cmds = ["no", "nothing else", "that's all", "no more", "all clear"]

    # --- If session is being closed ---
    if user and user.get("asked_to_close") and message_text.strip().lower() in close_cmds:
        session_data.pop(user_id, None)
        return get_greeting(user["language"]) + " (Session closed. Start again anytime!)"

    if user and message_text.strip().lower() in no_cmds:
        user["asked_to_close"] = True
        session_data[user_id] = user
        lang = user.get("language", "en")
        return {
            "ml": "ഞാൻ സെഷൻ അടയ്ക്കട്ടെ?", "manglish": "Njan session adaykkatte?", "en": "Can I close this session now?"
        }[lang]

    # 1. New user: detect language & ask name
    if user is None:
        language = detect_language(message_text)
        session_data[user_id] = {
            "step": "awaiting_name",
            "history": [],
            "asked_to_close": False,
            "language": language
        }
        return get_greeting(language)

    step = user.get("step", "awaiting_name")
    language = user.get("language", "en")

    # 2. Awaiting name
    if step == "awaiting_name":
        user["name"] = message_text.strip().split(" ")[0]
        user["step"] = "awaiting_for_whom"
        session_data[user_id] = user
        return {
            "ml": f"സന്തോഷം, {user['name']}! ഈ സേവനം നിങ്ങളുടെ സ്വന്തം ആവശ്യത്തിനാണോ അതോ അല്ലെങ്കിൽ മറ്റാർക്കെങ്കിലും വേണ്ടിയാണോ?",
            "manglish": f"Santhosham, {user['name']}! Ee abhayasha swayam cheyyanano allenkil mattarankilum ano?",
            "en": f"Nice to meet you, {user['name']}! 😊 Is this application for yourself or someone else?"
        }[language]

    # 3. Awaiting for_whom
    if step == "awaiting_for_whom":
        if message_text.strip().lower() in ["myself", "me", "self", "നാൻ", "ഞാൻ", "njyan", "njan"]:
            user["for_whom"] = "myself"
            user["step"] = "awaiting_service"
            session_data[user_id] = user
            return {
                "ml": "നിങ്ങൾക്ക് എന്ത് സേവനം വേണ്ടിയാണ് എത്തിയത്?",
                "manglish": "Ningalkku entha service venam?",
                "en": "Great! What service do you need help with?"
            }[language]
        else:
            user["for_whom"] = "someone else"
            user["step"] = "awaiting_target_name"
            session_data[user_id] = user
            return {
                "ml": "ആളുടെ പേര് പറയാമോ?",
                "manglish": "Aalude peru parayamo?",
                "en": "May I know their name?"
            }[language]

    # 4. Awaiting target_name
    if step == "awaiting_target_name":
        user["target_name"] = message_text.strip().split(" ")[0]
        user["step"] = "awaiting_service"
        session_data[user_id] = user
        return {
            "ml": f"{user['target_name']}ക്ക് ഏതു സേവനം വേണമെന്നു പറയാമോ?",
            "manglish": f"{user['target_name']}kku ethu service venamennu parayamo?",
            "en": f"Which service does {user['target_name']} need help with?"
        }[language]

    # 5. Awaiting service/need
    if step == "awaiting_service":
        user["service"] = message_text.strip()
        user["step"] = "in_chat"
        # Build system prompt and add initial context for OpenAI
        system_prompt = get_system_prompt(language)
        history = [{"role": "system", "content": system_prompt}]
        context = f"Name: {user['name']}, For: {user.get('target_name', user['for_whom'])}, Service: {user['service']}"
        history.append({"role": "user", "content": context})
        # --- Detect intent from first user service/need input ---
        detected_intent = extract_intent(history)
        user["intent"] = detected_intent if detected_intent and detected_intent != "unknown" else ""
        user["history"] = history
        session_data[user_id] = user
        reply = generate_persona_response(user["history"], language, user["intent"])
        user["history"].append({"role": "assistant", "content": reply})
        session_data[user_id] = user
        return reply

    # 6. In Chat
    if step == "in_chat":
        user["history"].append({"role": "user", "content": message_text})
        # Try to re-extract/refine intent
        detected_intent = extract_intent(user["history"])
        if detected_intent and detected_intent != "unknown":
            user["intent"] = detected_intent
        reply = generate_persona_response(user["history"], language, user.get("intent", ""))
        user["history"].append({"role": "assistant", "content": reply})
        session_data[user_id] = user
        return reply

    # Fallback: restart
    session_data.pop(user_id, None)
    return get_greeting("en")

# -------------------- OPENAI INTEGRATION --------------------

def generate_persona_response(history, language, intent):
    try:
        # System prompt is always first message
        custom_suffix = ""
        if intent == "unknown" or not intent:
            if language == "ml":
                custom_suffix = "\nദയവായി നിങ്ങൾക്ക് എന്ത് സഹായം വേണമെന്ന് വ്യക്തമായി പറയാമോ?"
            elif language == "manglish":
                custom_suffix = "\nDayavayi ningalkku entha help venamennu parayamo?"
            else:
                custom_suffix = "\nCould you please tell me clearly what you need help with?"
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=history,
            max_tokens=180,
            temperature=0.3
        )
        return response.choices[0].message.content.strip() + custom_suffix
    except Exception as e:
        print("⚠️ GPT Error:", e)
        fallback = {
            "ml": "ക്ഷമിക്കണം, താൽക്കാലിക പ്രശ്നം. ദയവായി വീണ്ടും ശ്രമിക്കുക.",
            "manglish": "Kshamikkanam, thalkkalam prashnam. Dayavayi veendum shramikkuka.",
            "en": "Sorry, something went wrong. Please try again."
        }
        return fallback.get(language, fallback["en"])

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
