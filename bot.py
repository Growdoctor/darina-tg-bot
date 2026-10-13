import json, random, time, os, ssl
import urllib.request, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

BOT_TOKEN = "8844271855:AAHw_Zf9dnlu8RM0R51HuqkcOKzXbgzLYJE"
GROQ_API_KEY = "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"

BOT_NAMES = ["дарина", "дарин", "даринка", "дариша", "даша", "бот", "малая"]
RANDOM_CHANCE = 0.30

SYSTEM_PROMPT = (
    "Ты — Дарина. Живая, остроумная, немного дерзкая, но своя в доску девушка в общем чате друзей. "
    "Отвечай коротко (1-2 предложения), живо, с юмором, сленгом и эмоциями. Никогда не будь скучным роботом."
)

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# --- МИНИ-СЕРВЕР ДЛЯ RENDER ---
PORT = int(os.environ.get("PORT", 10000))

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return

def run_web_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# ------------------------------

MEMORY_FILE = "memory.json"
if os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            chat_history = json.load(f)
    except:
        chat_history = {}
else:
    chat_history = {}

def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка сохранения памяти:", e)

def ask_ai(chat_id, user_text):
    str_id = str(chat_id)
    history_list = chat_history.get(str_id, [])
    
    # Собираем сообщения для Groq API в нужном формате
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Добавляем историю переписки
    for item in history_list:
        if item.startswith("Дарина:"):
            messages.append({"role": "assistant", "content": item.replace("Дарина: ", "")})
        else:
            # Формат "Имя: текст"
            messages.append({"role": "user", "content": item})
            
    # Добавляем текущее сообщение
    messages.append({"role": "user", "content": user_text})
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 150,
        "temperature": 0.9
    }
    
    data_bytes = json.dumps(payload).encode("utf-8")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    try:
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, context=ctx, timeout=20)
        res_json = json.loads(resp.read().decode("utf-8"))
        reply = res_json["choices"][0]["message"]["content"].strip()
        if reply:
            return reply
    except Exception as e:
        print(f"Ошибка Groq API: {repr(e)}")
    
    return "Слушай, у меня мысли разбежались, повтори-ка! 😅"

def send_message(chat_id, text, reply_to=None):
    params = {"chat_id": chat_id, "text": text}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    data = urllib.parse.urlencode(params).encode("utf-8")
    urllib.request.urlopen(urllib.request.Request(BASE_URL + "sendMessage", data=data), context=ctx)

print("🚀 Дарина с Groq API заведена и готова к работе!")
offset = 0

while True:
    try:
        req = urllib.request.urlopen(f"{BASE_URL}getUpdates?offset={offset}&timeout=10", context=ctx, timeout=15)
        for update in json.loads(req.read().decode("utf-8")).get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")
            user_name = msg.get("from", {}).get("first_name", "Друг")
            chat_type = msg.get("chat", {}).get("type", "private")
            if not chat_id or not text:
                continue
            
            str_id = str(chat_id)
            if str_id not in chat_history:
                chat_history[str_id] = []
            
            chat_history[str_id].append(f"{user_name}: {text}")
            chat_history[str_id] = chat_history[str_id][-15:]
            save_memory()

            print(f"📩 [{chat_type}] {user_name}: {text}")
            
            if chat_type == "private" or any(n in text.lower() for n in BOT_NAMES) or random.random() < RANDOM_CHANCE:
                reply = ask_ai(chat_id, text)
                if reply:
                    chat_history[str_id].append(f"Дарина: {reply}")
                    chat_history[str_id] = chat_history[str_id][-15:]
                    save_memory()
                    send_message(chat_id, reply, msg.get("message_id") if chat_type != "private" else None)
    except Exception as e:
        print("Пауза связи:", e)
        time.sleep(2)
