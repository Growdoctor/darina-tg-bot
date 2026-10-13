import urllib.request, urllib.parse, json, random, time, os, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

BOT_TOKEN = "8875515804:AAGGkZONqnPO0blpB83z_H1elgEV4DuBywY"
GEMINI_API_KEY = "AQ.Ab8RN6LI5HkMvB6kNxopRrQ2xfwmOMavjxMs3MlMcQv7CuK2_g"

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

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER FREE (ЗАПУСКАЕМ ПЕРВЫМ) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Darina is alive and working!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Запускаем веб-сервер в фоновом потоке, чтобы Render сразу обнаружил порт
threading.Thread(target=run_server, daemon=True).start()
# ----------------------------------------------------

# Загружаем память из файла, если он есть
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

# Автоматический поиск моделей
AVAILABLE_MODELS = []
try:
    models_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    req = urllib.request.urlopen(models_url, context=ctx, timeout=15)
    models_data = json.loads(req.read().decode("utf-8"))
    for m in models_data.get("models", []):
        name = m.get("name", "").replace("models/", "")
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods and "gemini" in name and "vision" not in name and "embedding" not in name:
            AVAILABLE_MODELS.append(name)
    AVAILABLE_MODELS.sort(key=lambda x: (0 if "flash" in x else 1, x), reverse=True)
except:
    AVAILABLE_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]

def ask_ai(chat_id):
    str_id = str(chat_id)
    history_text = "\n".join(chat_history.get(str_id, []))
    prompt = f"{SYSTEM_PROMPT}\n\nПереписка:\n{history_text}\n\nОтветь как Дарина (без слова 'Дарина:' в начале):"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    data_bytes = json.dumps(payload).encode("utf-8")

    for model in AVAILABLE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, context=ctx, timeout=25)
            res_json = json.loads(resp.read().decode("utf-8"))
            return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        except:
            continue
    return "Секунду, связь подвисла, напиши еще раз! ❤️"

def send_message(chat_id, text, reply_to=None):
    params = {"chat_id": chat_id, "text": text}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    data = urllib.parse.urlencode(params).encode("utf-8")
    urllib.request.urlopen(urllib.request.Request(BASE_URL + "sendMessage", data=data), context=ctx)

print("🚀 Дарина с долговременной памятью и веб-сервером запущена!")
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
            chat_history[str_id] = chat_history[str_id][-20:] # помнит последние 20 сообщений
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
