import urllib.request, urllib.parse, json, random, time, os, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

BOT_TOKEN = "8733403087:AAF0SjuCDji8IaX-JWoAM60xU59_RGzxe5Q"
GEMINI_API_KEY = "AQ.Ab8RN6I6D99IpbCoyc0-bsZZLzWg-NmM7DA7dhaNC6SSgyBsYg"

BOT_NAMES = ["дарина", "дарин", "даринка", "дариша", "даша", "бот", "малая"]
RANDOM_CHANCE = 0.30

SYSTEM_PROMPT = (
    "Тебя зовут Дарина. Ты живая, остроумная, немного дерзкая, но своя в доску девушка в общем чате друзей. "
    "Веди себя на 100% как реальная девчонка, пиши коротко (1-3 предложения), живо и с юмором. "
    "Рассуждай по теме разговора, подкалывай ребят, советуй что выпить из алкоголя или чем заняться вечером."
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

# Используем актуальные модели с поддержкой Bearer/OAuth токенов
AVAILABLE_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

def ask_ai(chat_id):
    str_id = str(chat_id)
    history_text = "\n".join(chat_history.get(str_id, []))
    prompt = f"{SYSTEM_PROMPT}\n\nПереписка:\n{history_text}\n\nОтветь как Дарина (без слова 'Дарина:' в начале):"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in AVAILABLE_MODELS:
        # Для ключей с префиксом AQ передаем авторизацию через заголовок Bearer
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GEMINI_API_KEY}"
        }
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=25)
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Ошибка с моделью {model}: {e}")
            continue
    return "Секунду, связь подвисла, напиши еще раз! ❤️"

def send_message(chat_id, text, reply_to=None):
    params = {"chat_id": chat_id, "text": text}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    data = urllib.parse.urlencode(params).encode("utf-8")
    urllib.request.urlopen(urllib.request.Request(BASE_URL + "sendMessage", data=data), context=ctx)

print("🚀 Дарина запущена с поддержкой нового типа ключа!")
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
            chat_history[str_id] = chat_history[str_id][-20:]
            save_memory()

            print(f"📩 [{chat_type}] {user_name}: {text}")
            if chat_type == "private" or any(n in text.lower() for n in BOT_NAMES) or random.random() < RANDOM_CHANCE:
                reply = ask_ai(chat_id)
                if reply:
                    chat_history[str_id].append(f"Дарина: {reply}")
                    chat_history[str_id] = chat_history[str_id][-20:]
                    save_memory()
                    send_message(chat_id, reply, msg.get("message_id") if chat_type != "private" else None)
    except Exception as e:
        print("Пауза связи:", e)
        time.sleep(2)
