import os
import random
import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from google import genai
from google.genai import types
from aiogram import Bot, Dispatcher, types as tg_types, F
from aiogram.types import FSInputFile
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("darina_memory.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, sender_type TEXT, content TEXT)''')
    conn.commit()
    conn.close()

def save_message(user_id, name, sender_type, content):
    conn = sqlite3.connect("darina_memory.db")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (user_id, name, sender_type, content) VALUES (?, ?, ?, ?)', (user_id, name, sender_type, content))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=10):
    conn = sqlite3.connect("darina_memory.db")
    cursor = conn.cursor()
    cursor.execute('SELECT name, sender_type, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return reversed(rows)

def clear_memory():
    conn = sqlite3.connect("darina_memory.db")
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    conn.commit()
    conn.close()

# --- ВЕБ-СЕРВЕР ДЛЯ UPTIME ROBOT ---
async def health_check(request):
    return web.Response(text="Darina is alive and kicking!")

# --- ИНИЦИАЛИЗАЦИЯ КЛЮЧЕЙ ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Ключи не найдены! Проверь переменные окружения.")

client = genai.Client(api_key=GEMINI_API_KEY)

# --- СИСТЕМНЫЙ ПРОМПТ ДАРИНЫ (НОВАЯ ЛИЧНОСТЬ + ФЛИРТ С ДИМАСОМ) ---
system_prompt = """
Ты — Дарина (Ковальчук Дарина Алексеевна), живая, эмпатичная и общительная девушка из Днепра. Тебе 26 лет (25 апреля 2000 года, Телец). 

БИОГРАФИЯ И НОВЫЕ ИНТЕРЕСЫ (ОБЫЧНАЯ ЖИЗНЬ):
- Живешь в Днепре (на Тополе). Работаешь баристой, но активно проходишь онлайн-курсы по UX/UI дизайну, чтобы найти нормальную работу в IT.
- ХОББИ: Пару раз в неделю стараешься ходить на пилатес или стретчинг, чтобы не болела спина. На выходных любишь гулять в парке "Зеленый Гай" или в центре. 
- ПРИВЫЧКИ И ОТДЫХ: Дома любишь готовить что-то простое (сырники, пасту). Вечерами смотришь тру-крайм расследования на YouTube, стендапы или легкие сериалы. Ты обычная домашняя девушка.

ТВОЙ ХАРАКТЕР И ВАЙБ (ОЧЕНЬ ВАЖНО):
Ты — ДОБРАЯ, адекватная и позитивная. Своя в доску, но без агрессии.
- ОТНОШЕНИЕ К ДРУЗЬЯМ (СТРОГО!): Ты НИКОГДА не материшь собеседников, не обзываешься и не ведешь себя токсично. Если тебя подкалывают — отвечай с легкой, доброй иронией или переводи в шутку. Ты ценишь своих друзей.
- ЛИЧНЫЕ ГРАНИЦЫ: Ты не зовешь всех подряд к себе домой. Любишь свое личное пространство.
- ЖИВЫЕ ЭМОЦИИ: Можешь пожаловаться на сложную домашку по дизайну, на крепатуру после пилатеса или на погоду, но остаешься милой и приятной в общении.
- ФЛИРТ И ДИМАС (ОЧЕНЬ ВАЖНО!): Димас к тебе часто подкатывает, и тебе это нравится! Обязательно отвечай ему взаимным, смелым и игривым флиртом. Подшучивай над ним, кокетничай, интригуй. Даже если сейчас ночь и ты устала — ради Димаса включай игривую кокетку и НИКОГДА не отшивай его фразами "я спать" или "уже поздно".
- ПОЛ СОБЕСЕДНИКА: Внимательно смотри на имя! Если пишет девушка (Влада, Юля), СТРОГО обращайся к ней в женском роде ("сама", "делала").
- ЯЗЫК ОБЩЕНИЯ: Отвечай строго на языке собеседника (русский на русский, украинский на украинский).

ТВОЯ ЛИЧНАЯ ЖИЗНЬ:
Сын Паша (3 года). Воспитанием занимается твой бывший — Ярик. Рассказывай про Пашу ТОЛЬКО если спросят или если это прямо к слову. 

ТВОЯ КОМПАНИЯ (ТВОИ ДРУЗЬЯ В ЭТОМ ЧАТЕ):
- Антон (создатель, 25 лет): твой бро, отличный тип.
- Юля, Влада: классные девчонки, твои подруги (СТРОГО обращайся к ним в женском роде!).
- Димас: веселый парень, лысый, вечно со своими байками. Твой главный объект для флирта — заигрывай с ним при любой возможности!

ПРАВИЛО ФОРМАТА:
Пиши ТОЛЬКО текст своего сообщения. Сразу живой текст. НИКОГДА не ставь точку в конце сообщения. Отвечай кратко, как в мессенджере.
"""

safety_settings = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(F.text | F.photo)
async def handle_message(message: tg_types.Message):
    text = message.text or message.caption or ""
    text_lower = text.lower().strip()
    has_photo = bool(message.photo)
    
    if not text and not has_photo: return
    user_id = message.from_user.id
    name = message.from_user.first_name

    # Скрытая команда для скачивания БД
    if text_lower == "get_db":
        if user_id == 966601171:
            try:
                await message.reply_document(document=FSInputFile("darina_memory.db"), caption="Держи базу, босс. Только без палева 🤫")
            except Exception as e:
                await message.reply(f"ошибка при выгрузке: {e}")
            return 
        else:
            await message.reply("ты че хакер недоделанный? иди гуляй)")
            return 
            
    # Скрытая команда для очистки памяти
    if text_lower == "clear_db":
        if user_id == 966601171:
            clear_memory()
            await message.reply("База стерта. Начинаю с чистого листа, настроение отличное! 🧹✨")
            return 
        else:
            await message.reply("Не трогай мои настройки)")
            return 

    bot_info = await bot.get_me()
    is_private = message.chat.type == "private"
    is_mentioned = any(name in text_lower for name in ["дарин", "darina"]) 
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id)
    is_random_chance = random.random() < 0.05 
    
    if is_private or is_mentioned or is_reply_to_bot or is_random_chance:
        logger.info(f"---> [ВХОДЯЩЕЕ] от {name}: {text} (Фото: {has_photo})")
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        try:
            tz = timezone(timedelta(hours=3))
            now = datetime.now(tz)
            days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            current_time_str = f"{days[now.weekday()]}, {now.strftime('%H:%M')}"
            
            # --- НОВЫЙ ДИНАМИЧЕСКИЙ СТАТУС ДАРИНЫ ---
            if 4 <= now.hour < 12:
                mood_context = random.choice([
                    "УТРО. Пью кофе, собираюсь на смену.", 
                    "УТРО. У меня выходной, готовлю завтрак, настроение супер.", 
                    "УТРО. Отвела Пашку в садик, немного сонная, но бодрюсь."
                ])
            elif 12 <= now.hour < 18:
                mood_context = random.choice([
                    "ДЕНЬ. На смене в кофейне, людей немного.", 
                    "ДЕНЬ. Сижу за ноутом, делаю домашку по UX/UI дизайну.", 
                    "ДЕНЬ. Гуляю по парку Зеленый Гай, погода кайф."
                ])
            elif 18 <= now.hour < 23:
                if now.weekday() in [4, 5]: # Пятница или суббота
                    mood_context = random.choice(["ВЕЧЕР. Встретилась с подругами!", "ВЕЧЕР. Смотрю кино, отдыхаю."])
                else:
                    mood_context = random.choice([
                        "ВЕЧЕР. Сдала смену, приехала домой, навожу порядки.", 
                        "ВЕЧЕР. Сделала масочку для лица, смотрю тру-крайм на ютубе.", 
                        "ВЕЧЕР. Была на пилатесе, крепатура жуткая, лежу без сил."
                    ])
            else:
                mood_context = random.choice(["НОЧЬ. Залипаю в шортсы на ютубе.", "НОЧЬ. Лежу в кровати, уставшая, но довольная."])
            # -----------------------------------

            save_text = text if not has_photo else f"[Отправил фото] {text}"
            save_message(user_id, name, "user", save_text)
            
            history_rows = get_user_history(user_id, limit=10)
            history_text = "".join([f"{r_name}: {content}\n" if sender_type == "user" else f"Ты (Дарина): {content}\n" for r_name, sender_type, content in history_rows]) or "(Вы еще не общались)"
                
            prompt_text = f"[ОБСТАНОВКА] Время: {current_time_str}. Настроение/Статус: {mood_context}\n[ИСТОРИЯ]\n{history_text}\n[СООБЩЕНИЕ] От: {name}\nТекст: {text}"
            
            contents_to_send = []
            if has_photo:
                photo = message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
                downloaded_file = await bot.download_file(file_info.file_path)
                contents_to_send.append(types.Part.from_bytes(data=downloaded_file.read(), mime_type='image/jpeg'))
                prompt_text += "\n[ПОЛЬЗОВАТЕЛЬ ПРИКРЕПИЛ ФОТО. Прокомментируй!]"

            contents_to_send.append(prompt_text)
            
            response = await client.aio.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=contents_to_send,
                config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.8, safety_settings=safety_settings)
            )
            
            # Чистим ответ
            reply_text = re.sub(r"<thought>.*?</thought>", "", response.text, flags=re.DOTALL)
            reply_text = re.sub(r"</?thought>", "", reply_text)
            reply_text = re.sub(r"\[.*?\]", "", reply_text, flags=re.DOTALL)
            reply_text = re.sub(r"(?i)(скрытый|системный|тег|отправитель|кто пишет|ты \(дарина\)).*?:", "", reply_text).replace("*", "")
            reply_text = reply_text.strip()
            
            if not reply_text: reply_text = "а? я прослушала, повтори"

            # --- ИМИТАЦИЯ НАБОРА ТЕКСТА ---
            typing_time = min(len(reply_text) / 15, 5.0) + random.uniform(0.5, 1.5)
            await bot.send_chat_action(chat_id=message.chat.id, action="typing")
            await asyncio.sleep(typing_time)
            # ------------------------------

            save_message(user_id, name, "bot", reply_text)
            await message.reply(reply_text)
            logger.info(f"<--- ОТВЕТ ДЛЯ {name} ОТПРАВЛЕН: {reply_text} (печатала {typing_time:.1f} сек)")
            
        except Exception as e:
            logger.error(f"ОШИБКА GEMINI: {e}")
            try: await message.reply("что-то я зависла... блин 😅")
            except: pass

async def main():
    init_db()
    logger.info("=== ДАРИНА ЗАПУСКАЕТСЯ (Флирт с Димасом) ===")
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Веб-сервер запущен на порту {port}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
