import os
import json
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
from supabase import create_client, Client

app = Flask(__name__)

# --- VARIABLES DE ENTORNO DE META ---
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "EAARfCmIXDPMBSCdn3ZAeY1nw7opljj9QFf7yJYSMgclUbOmtykBdzxI4If3BZAI0uSOZCOj5pUiiOCPpRvZCiG1GSZBSiyeLuZCroHRLBxUxVoYRnJgN0l33tHYojlEu0jBrqIS91G6RyECGgCnR5oFzgXXbEZBbsICQAjs7AXDwmlpg1CJAG1tHskqwcpZAlYINHgZDZD")
PHONE_NUMBER_ID = os.getenv("META_PHONE_ID", "1324687800726958")
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "mi_token_secreto_hotel_123")

# --- CONFIGURACIÓN DE SUPABASE Y GEMINI ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error conectando a Supabase: {e}")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Carga de credenciales JSON de Google
def load_google_json():
    json_env = os.getenv("GOOGLE_CREDENTIALS_ENV")
    if json_env:
        return json.loads(json_env)
    if os.path.exists("credentials.json"):
        with open("credentials.json", "r") as f:
            return json.load(f)
    return None

google_creds = load_google_json()
user_sessions = {}

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    return 'Token inválido', 403

@app.route('/webhook', methods=['POST'])
def receive_message():
    data = request.get_json()
    try:
        if 'entry' in data:
            for entry in data['entry']:
                for change in entry['changes']:
                    value = change['value']
                    if 'messages' in value:
                        for message in value['messages']:
                            phone_number = message['from']
                            msg_body = message.get('text', {}).get('body', '').strip()
                            if msg_body:
                                process_user_message(phone_number, msg_body)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return jsonify({"status": "error"}), 500

def process_user_message(phone_number, text):
    try:
        if GEMINI_API_KEY:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(text)
            reply = response.text
        else:
            reply = f"Servidor activo. Mensaje recibido: '{text}'"
    except Exception as e:
        print(f"Error con Gemini: {e}")
        reply = "Servidor recibido, pero hubo un detalle al consultar la IA."

    send_whatsapp_message(phone_number, reply)

def send_whatsapp_message(to_number, text):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, json=payload, headers=headers)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
                            
