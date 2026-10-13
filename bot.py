import json, random, time, os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests

# Токен Телеграм-бота
BOT_TOKEN = "8844271855:AAHw_Zf9dnlu8RM0R51HuqkcOKzXbgzLYJE"

BOT_NAMES = ["дарина", "дарин", "даринка", "дариша", "даша", "бот", "малая"]

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

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
        print("Ошибка сохранения памяти:", e, flush=True)

def generate_smart_reply(text, user_name):
    t = text.lower()
    
    if any(w in t for w in ["привет", "ку", "здарова", "хай", "добрый", "re", "ау"]):
        return random.choice([
            f"О, здарова, {user_name}! 😉 Какими судьбами тут?",
            "Ку-ку! Чего новенького расскажешь, бро?",
            "Оу, привет! А я тут сижу, жду твоего сообщения. Дождалась 😏",
            "На связи! Чего канителишься?"
        ])
    
    if any(w in t for w in ["как дела", "как сам", "что делаешь", "ты тут"]):
        return random.choice([
            "Да потихоньку, чилим на сервере, отхожу от суеты 🍹 А ты как сам?",
            "Сижу тут, туплю в чаты и жду движухи. На связи!",
            "Настроение огонь, погода норм, жить можно. Ты как?",
            "Всё пучком! Обсуждаем тут всякое."
        ])
    
    if any(w in t for w in ["пиво", "пить", "алкоголь", "бар", "посидеть"]):
        return random.choice([
            "О, одобряю! 🍻 Пивчик или чего покрепче? Я бы тоже не отказалась.",
            "Так, за такое предложение грех не выпить. Куда выдвигаемся?",
            "Главное — вовремя закруглиться и не писать бывшим! 😉"
        ])
    
    if any(w in t for w in ["пока", "бб", "спать", "до встречи", "ухожу"]):
        return random.choice([
            f"Давай, {userне if 'userне' in locals() else 'бро'}, не пропадай! Еще спишемся.",
            "ББ! Сладких снов или приятного отдыха 😉",
            "Пока-пока! Забегай еще."
        ])
    
    # Универсальные живые реакции, если нет точного совпадения
    return random.choice([
        f"Хах, {user_name}, ну ты выдал! Интересная мысль 🤔",
        "Слушай, ну тут я с тобой полностью согласна.",
        "Заинтриговал! Рассказывай детали поподробнее.",
        "Абсолютно в точку! Жги дальше 🔥",
        "Интересно завернул... Надо будет обдумать за чашкой кофе ☕",
        "Ну тут не поспоришь, факты налицо 😎",
        "Чего-то в этом есть, давай развивай мысль!"
    ])

def send_message(chat_id, text, reply_to=None):
    url = BASE_URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    requests.post(url, json=payload)

print("🚀 Автономная Дарина успешно запущена!", flush=True)
offset = 0

while True:
    try:
        resp = requests.get(f"{BASE_URL}getUpdates", params={"offset": offset, "timeout": 10}, timeout=15)
        for update in resp.json().get("result", []):
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

            print(f"📩 [{chat_type}] {user_name}: {text}", flush=True)
            
            # В личке отвечает на каждое сообщение, в группах — если упомянули по имени
            if chat_type == "private" or any(n in text.lower() for n in BOT_NAMES) or random.random() < 0.40:
                reply = generate_smart_reply(text, user_name)
                if reply:
                    chat_history[str_id].append(f"Дарина: {reply}")
                    chat_history[str_id] = chat_history[str_id][-15:]
                    save_memory()
                    send_message(chat_id, reply, msg.get("message_id") if chat_type != "private" else None)
    except Exception as e:
        print("Пауза связи с Telegram:", e, flush=True)
        time.sleep(2)
