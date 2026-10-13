import urllib.request, urllib.parse, json, random, time, os, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

BOT_TOKEN = "8844271855:AAHw_Zf9dnlu8RM0R51HuqkcOKzXbgzLYJE"

BOT_NAMES = ["дарина", "дарин", "даринка", "дариша", "даша", "бот", "малая"]
RANDOM_CHANCE = 0.35

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# --- МИНИ-СЕРВЕР ДЛЯ RENDER (ПОДДЕРЖАНИЕ СТАТУСА LIVE) ---
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
# ---------------------------------------------------------

# Память чатов
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

# Умный движок ответов Дарины в ее фирменном стиле
def get_darina_response(text, user_name):
    t = text.lower()
    
    if any(w in t for w in ["привет", "ку", "здарова", "хай", "добрый день", "вечер"]):
        return random.choice([
            f"О, здарова, {user_name}! 😉 Какими судьбами в нашем богом забытом чате?",
            f"Ку-ку, {user-name if 'user-name' in locals() else 'дружище'}! Чего новенького рассказываешь?",
            "Оу, привет! А я тут сижу, думаю, какому бы красавчику написать. Написал ты 😏"
        ])
    
    if any(w in t for w in ["как дела", "как сам", "что делаешь", "как жизнь"]):
        return random.choice([
            "Да потихоньку, чилим в облаках Render, отхожу от вчерашнего 🍹 А ты как?",
            "Сижу в интернете, туплю в монитор и жду пока мне норм тему для разговора подкинут. Ты как?",
            "Всё пучком! Настроение огонь, погода норм, жить можно."
        ])
    
    if any(w in t for w in ["пиво", "пить", "алкоголь", "вино", "водка", "бар", "посидеть"]):
        return random.choice([
            "О, одобряю! 🍻 Пивчик или чего покрепче? Я бы сейчас не отказалась от холодного сидра.",
            "Так, ну за такое предложение грех не выпить. Куда выдвигаемся?",
            "Обожаю эту тему. Главное — вовремя закусить и не писать бывшим после третьей рюмок! 😉"
        ])
    
    if any(w in t for w in ["музыка", "трек", "песня", "слушать", "скачать"]):
        return random.choice([
            "Ой, музыка — это святое. Без нормального рэпчика или качающего бита вообще никуда.",
            "Скинь название трека, послушаю вместе с тобой! 🎧",
            "Музыка под настроение — это наше всё. Что слушаешь обычно?"
        ])
    
    if any(w in t for w in ["бот", "дарина", "ты кто"]):
        return random.choice([
            "Я? Твоя любимая виртуальная подруга Дарина, между прочим! 😎",
            "Я тут главная по вайбу и хорошему настроению. Несогласные могут выйти из чата)",
            "Твой персональный искуситель скуки. Чего хотел?"
        ])
    
    # Универсальные дерзкие и живые ответы, если тема не распознана
    return random.choice([
        f"Хах, {user_name}, ну ты выдал! Даже не знаю, что на это ответить 🤔",
        "Интересная мысль... Надо будет обдумать за чашечкой кофе (или пива 🍻).",
        "Ну тут ты прав на все сто, спорить даже не буду.",
        "Абсолютно согласна! Жги дальше, мне нравится ход твоих мыслей 😏",
        "Слушай, ну звучит как план. А давай подробнее?",
        "Честно? Заинтриговал. Рассказывай детали!"
    ])

def send_message(chat_id, text, reply_to=None):
    params = {"chat_id": chat_id, "text": text}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    data = urllib.parse.urlencode(params).encode("utf-8")
    urllib.request.urlopen(urllib.request.Request(BASE_URL + "sendMessage", data=data), context=ctx)

print("🚀 Дарина успешно запущена и ждет сообщения!")
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
            
            # Отвечаем в личке, если упомянули по имени, или с вероятностью рандома
            if chat_type == "private" or any(n in text.lower() for n in BOT_NAMES) or random.random() < RANDOM_CHANCE:
                reply = get_darina_response(text, user_name)
                if reply:
                    chat_history[str_id].append(f"Дарина: {reply}")
                    chat_history[str_id] = chat_history[str_id][-20:]
                    save_memory()
                    send_message(chat_id, reply, msg.get("message_id") if chat_type != "private" else None)
    except Exception as e:
        print("Пауза связи:", e)
        time.sleep(2)
