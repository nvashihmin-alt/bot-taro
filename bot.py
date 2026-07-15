import asyncio
import random
import datetime
import aiohttp
import aiosqlite
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.filters import Command

# ===================== ЛОГИРОВАНИЕ =====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================== КОНФИГУРАЦИЯ =====================
TOKEN = None
OPENROUTER_API_KEY = None
API_URL = "https://openrouter.ai/api/v1/chat/completions"
DB = "tarot.db"
FREE_LIMIT = 10

# ===================== ПОЛНАЯ КОЛОДА ТАРО =====================
MAJOR_ARCANA = [
    "Шут", "Маг", "Верховная Жрица", "Императрица", "Император",
    "Иерофант", "Влюбленные", "Колесница", "Сила", "Отшельник",
    "Колесо Фортуны", "Справедливость", "Повешенный", "Смерть",
    "Умеренность", "Дьявол", "Башня", "Звезда", "Луна", "Солнце",
    "Страшный Суд", "Мир"
]

SUITS = {
    "Жезлы": "🔥 Огонь",
    "Кубки": "💧 Вода",
    "Мечи": "💨 Воздух",
    "Пентакли": "🌍 Земля"
}

MINOR_ARCANA = []
for suit in SUITS.keys():
    for rank in ["Туз", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Паж", "Рыцарь", "Королева", "Король"]:
        MINOR_ARCANA.append(f"{rank} {suit}")

ALL_CARDS = MAJOR_ARCANA + MINOR_ARCANA

# ===================== ПЕРЕВЕРНУТЫЕ КАРТЫ =====================
REVERSED_CHANCE = 0.3

def draw_card_with_reversed():
    card = random.choice(ALL_CARDS)
    is_reversed = random.random() < REVERSED_CHANCE
    return card, is_reversed

def make_spread(spread_type: str):
    count = SPREADS[spread_type]["count"]
    cards = []
    for _ in range(count):
        card, is_reversed = draw_card_with_reversed()
        cards.append({
            "name": card,
            "is_reversed": is_reversed,
            "emoji": "🔄" if is_reversed else "⬆️"
        })
    return cards

# ===================== НУМЕРОЛОГИЯ =====================
def get_zodiac_sign(day: int, month: int):
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "Овен ♈"
    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "Телец ♉"
    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "Близнецы ♊"
    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "Рак ♋"
    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "Лев ♌"
    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "Дева ♍"
    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "Весы ♎"
    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "Скорпион ♏"
    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "Стрелец ♐"
    elif (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "Козерог ♑"
    elif (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "Водолей ♒"
    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return "Рыбы ♓"
    return None

def get_life_path_number(birth_date: str):
    digits = [int(d) for d in birth_date if d.isdigit()]
    total = sum(digits)
    while total > 9 and total not in [11, 22, 33]:
        total = sum(int(d) for d in str(total))
    return total

def get_destiny_number(birth_date: str):
    parts = birth_date.split('.')
    if len(parts) == 3:
        day_sum = sum(int(d) for d in parts[0])
        month_sum = sum(int(d) for d in parts[1])
        year_sum = sum(int(d) for d in parts[2])
        
        while day_sum > 9:
            day_sum = sum(int(d) for d in str(day_sum))
        while month_sum > 9:
            month_sum = sum(int(d) for d in str(month_sum))
        while year_sum > 9:
            year_sum = sum(int(d) for d in str(year_sum))
        
        total = day_sum + month_sum + year_sum
        while total > 9 and total not in [11, 22, 33]:
            total = sum(int(d) for d in str(total))
        return total
    return None

def get_soul_urge_number(birth_date: str):
    digits = [int(d) for d in birth_date if d.isdigit()]
    total = sum(digits)
    while total > 9 and total not in [11, 22]:
        total = sum(int(d) for d in str(total))
    return total

def get_birth_day_number(day: int):
    while day > 9:
        day = sum(int(d) for d in str(day))
    return day

def get_personality_number(birth_date: str):
    parts = birth_date.split('.')
    if len(parts) >= 2:
        day = int(parts[0])
        month = int(parts[1])
        total = day + month
        while total > 9:
            total = sum(int(d) for d in str(total))
        return total
    return None

def get_numerology_interpretation(number: int):
    interpretations = {
        1: "Лидер, новатор, независимость",
        2: "Дипломат, партнерство, чувствительность",
        3: "Творчество, общение, оптимизм",
        4: "Стабильность, порядок, трудолюбие",
        5: "Свобода, приключения, перемены",
        6: "Ответственность, семья, гармония",
        7: "Мудрость, анализ, духовность",
        8: "Власть, успех, материальное",
        9: "Гуманизм, завершение, сострадание",
        11: "Интуиция, вдохновение, просветление",
        22: "Великий строитель, мастер-строитель",
        33: "Мастер-учитель, безусловная любовь"
    }
    return interpretations.get(number, "Уникальная комбинация энергий")

def get_gender_emoji(gender: str):
    if gender == "Мужской":
        return "👨"
    elif gender == "Женский":
        return "👩"
    return "🧑"

# ===================== СЛУЧАЙНЫЕ СОВЕТЫ =====================
DAILY_ADVICE = [
    "🌟 Доверяй своей интуиции — она ведет тебя правильным путем.",
    "🌱 Каждое препятствие — это возможность для роста.",
    "💫 Вселенная всегда на твоей стороне, просто откройся ей.",
    "🔥 Твоя сила внутри тебя — не забывай об этом.",
    "🌈 После дождя всегда выходит солнце.",
    "🦋 Не бойся перемен — они ведут к лучшей версии тебя.",
    "✨ Ты создаешь свою реальность каждым своим выбором.",
    "🌙 Лунный свет освещает путь даже в самой темной ночи.",
    "🌺 Будь благодарен за то, что имеешь, и придет еще больше.",
    "⭐ Твоя звезда ярко сияет — верь в себя!",
    "🌊 Как океан, прими все эмоции — они временны.",
    "🍃 Отпусти то, что не служит тебе, и освободи место для нового.",
    "🎯 Сосредоточься на том, что действительно важно.",
    "💎 Ты ценен уже просто потому, что ты есть.",
    "🌅 Каждый новый день — это новый шанс."
]

def get_random_advice():
    return random.choice(DAILY_ADVICE)

# ===================== ТИПЫ РАСКЛАДОВ =====================
SPREADS = {
    "1_карта": {
        "name": "Карта дня",
        "emoji": "⭐",
        "count": 1,
        "positions": ["Главный совет на сегодня"],
        "description": "Быстрый ответ на вопрос 'Что меня ждет сегодня?'"
    },
    "3_карты": {
        "name": "Прошлое-Настоящее-Будущее",
        "emoji": "🔮",
        "count": 3,
        "positions": ["Прошлое", "Настоящее", "Будущее"],
        "description": "Классический расклад на ситуацию"
    },
    "5_карт": {
        "name": "Выбор пути",
        "emoji": "⚖️",
        "count": 5,
        "positions": ["Ситуация", "Вариант А", "Вариант Б", "Результат А", "Результат Б"],
        "description": "Поможет принять решение"
    },
    "7_карт": {
        "name": "Отношения",
        "emoji": "❤️",
        "count": 7,
        "positions": ["Ты", "Партнер", "Отношения сейчас", "Что ждет тебя", "Что ждет партнера", "Будущее отношений", "Совет"],
        "description": "Расклад на любовь и отношения"
    },
    "10_карт": {
        "name": "Кельтский крест",
        "emoji": "⚔️",
        "count": 10,
        "positions": ["Текущая ситуация", "Препятствие", "Прошлое", "Будущее", "Над тобой", "Под тобой", "Совет", "Внешнее", "Внутреннее", "Итог"],
        "description": "Самый глубокий и полный расклад"
    }
}

user_state = {}

# ===================== БАЗА ДАННЫХ =====================
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_premium INTEGER DEFAULT 0,
            requests_today INTEGER DEFAULT 0,
            last_date TEXT,
            birth_date TEXT,
            gender TEXT,
            registered BOOLEAN DEFAULT 0
        )
        """)
        
        cursor = await db.execute("PRAGMA table_info(users)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'birth_date' not in column_names:
            await db.execute("ALTER TABLE users ADD COLUMN birth_date TEXT")
            logger.info("✅ Добавлена колонка birth_date")
        
        if 'gender' not in column_names:
            await db.execute("ALTER TABLE users ADD COLUMN gender TEXT")
            logger.info("✅ Добавлена колонка gender")
            
        if 'registered' not in column_names:
            await db.execute("ALTER TABLE users ADD COLUMN registered BOOLEAN DEFAULT 0")
            logger.info("✅ Добавлена колонка registered")
        
        await db.commit()

async def get_user(user_id: int):
    today = str(datetime.date.today())
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users(user_id, last_date) VALUES(?, ?)",
            (user_id, today)
        )
        await db.commit()
        cur = await db.execute(
            "SELECT is_premium, requests_today, last_date, birth_date, gender, registered FROM users WHERE user_id=?",
            (user_id,)
        )
        row = await cur.fetchone()
        is_premium, req, last_date, birth_date, gender, registered = row
        if last_date != today:
            req = 0
            await db.execute(
                "UPDATE users SET requests_today=0, last_date=? WHERE user_id=?",
                (today, user_id)
            )
            await db.commit()
        return is_premium, req, birth_date, gender, registered

async def update_requests(user_id: int, value: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET requests_today=? WHERE user_id=?",
            (value, user_id)
        )
        await db.commit()

async def save_user_data(user_id: int, birth_date: str, gender: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE users SET birth_date=?, gender=?, registered=1 WHERE user_id=?",
            (birth_date, gender, user_id)
        )
        await db.commit()

# ===================== КЛАВИАТУРЫ =====================
gender_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👨 Мужской")],
        [KeyboardButton(text="👩 Женский")]
    ],
    resize_keyboard=True
)

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Карта дня"), KeyboardButton(text="🔮 3 карты")],
        [KeyboardButton(text="⚖️ 5 карт"), KeyboardButton(text="❤️ 7 карт")],
        [KeyboardButton(text="⚔️ Кельтский крест")],
        [KeyboardButton(text="♈ Гороскоп"), KeyboardButton(text="🔢 Нумерология")],
        [KeyboardButton(text="💎 Премиум")]
    ],
    resize_keyboard=True
)

# ===================== API ЗАПРОСЫ =====================
async def generate_interpretation(cards: list, spread_type: str, birth_date: str = None, gender: str = None):
    spread = SPREADS[spread_type]
    positions = spread["positions"]
    
    cards_with_positions = []
    for i, card_info in enumerate(cards):
        card_name = card_info["name"]
        is_reversed = card_info["is_reversed"]
        status = "🔄 перевернута" if is_reversed else "⬆️ прямая"
        cards_with_positions.append(f"{positions[i]}: {card_name} ({status})")
    
    cards_text = "\n".join(cards_with_positions)
    
    numerology_context = ""
    if birth_date:
        try:
            day, month = map(int, birth_date.split('.'))
            zodiac = get_zodiac_sign(day, month)
            life_path = get_life_path_number(birth_date)
            destiny = get_destiny_number(birth_date)
            
            numerology_context = f"""
Данные пользователя:
- Дата рождения: {birth_date}
- Знак зодиака: {zodiac}
- Число жизненного пути: {life_path} ({get_numerology_interpretation(life_path)})
- Число судьбы: {destiny} ({get_numerology_interpretation(destiny)})
- Пол: {gender}
"""
        except:
            pass
    
    prompt = f"""
Ты — опытный таролог с 20-летним стажем. Сделай подробный расклад.

Выпавшие карты:
{cards_text}

{numerology_context}

Инструкция по толкованию:
1. Для КАЖДОЙ карты дай развернутое значение (3-4 предложения) в контексте её позиции
2. ОБЯЗАТЕЛЬНО учти, перевернута карта или нет
3. Учти нумерологические данные пользователя в толковании
4. Опиши, как карты взаимодействуют друг с другом
5. Дай общий итоговый вывод и совет

Отвечай на русском языке, красивым литературным слогом, с долей мистицизма.
"""
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/your_bot",
            "X-Title": "Tarot Bot"
        }
        
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Ты — мудрый таролог. Отвечай структурированно, глубоко и вдохновляюще."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 800
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка API: {response.status} - {error_text}")
                    return generate_fallback_interpretation(cards, positions)
                    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return generate_fallback_interpretation(cards, positions)

def generate_fallback_interpretation(cards: list, positions: list):
    result = []
    for i, card_info in enumerate(cards):
        card_name = card_info["name"]
        status = "🔄 перевернута" if card_info["is_reversed"] else "⬆️ прямая"
        
        suit_info = ""
        for suit in SUITS:
            if suit in card_name:
                suit_info = f" {SUITS[suit]}"
                break
        
        result.append(f"• <b>{positions[i]}</b>: {card_name}{suit_info} {status}")
    return "\n".join(result)

async def generate_horoscope(birth_date: str, gender: str):
    day, month = map(int, birth_date.split('.'))
    zodiac = get_zodiac_sign(day, month)
    lucky_number = get_life_path_number(birth_date)
    
    prompt = f"""
Ты — опытный астролог. Составь персональный гороскоп.

Дата рождения: {birth_date}
Знак зодиака: {zodiac}
Счастливое число: {lucky_number}
Пол: {gender}

Напиши:
1. Краткую характеристику знака с учетом пола (2-3 предложения)
2. Прогноз на сегодня (энергетика, настроение, события)
3. Совет по взаимодействию с другими людьми
4. Вдохновляющую фразу на день

Отвечай на русском языке, красиво и вдохновляюще.
"""
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Ты — мудрый астролог. Отвечай вдохновляюще и с душой."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['choices'][0]['message']['content']
                else:
                    return f"🌟 Сегодня отличный день для новых начинаний, {zodiac}!"
    except:
        return f"🌟 Сегодня отличный день для новых начинаний, {zodiac}!"

# ===================== ОБРАБОТЧИКИ =====================
# Обработчики теперь используют функцию-замыкание, чтобы получить доступ к dp
def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики в диспетчере"""
    
    @dp.message(Command("start"))
    async def start(message: Message):
        await init_db()
        user_id = message.from_user.id
        _, _, birth_date, gender, registered = await get_user(user_id)
        
        if registered and birth_date and gender:
            await show_main_menu(message)
        else:
            user_state[user_id] = {"step": "birth_date"}
            await message.answer(
                "🔮 <b>Добро пожаловать в Таро-бот!</b>\n\n"
                "Для персонализированных раскладов и гороскопов мне нужны ваши данные.\n\n"
                "📅 Введите вашу <b>дату рождения</b> в формате <b>ДД.ММ</b> (например, 15.06):",
                parse_mode="HTML"
            )

    async def show_main_menu(message: Message):
        user_id = message.from_user.id
        _, _, birth_date, gender, _ = await get_user(user_id)
        
        try:
            day, month = map(int, birth_date.split('.'))
            zodiac = get_zodiac_sign(day, month)
            life_path = get_life_path_number(birth_date)
            gender_emoji = get_gender_emoji(gender)
        except:
            zodiac = "⭐"
            life_path = "?"
            gender_emoji = "🧑"
        
        await message.answer(
            f"🔮 <b>Главное меню</b>\n\n"
            f"{gender_emoji} {gender} | {zodiac}\n"
            f"🔢 Число жизненного пути: {life_path}\n\n"
            f"Выбери тип расклада:\n"
            f"• ⭐ <b>Карта дня</b> — быстрый совет\n"
            f"• 🔮 <b>3 карты</b> — прошлое-настоящее-будущее\n"
            f"• ⚖️ <b>5 карт</b> — выбор пути\n"
            f"• ❤️ <b>7 карт</b> — отношения\n"
            f"• ⚔️ <b>Кельтский крест</b> — полный расклад\n\n"
            f"• ♈ <b>Гороскоп</b> — персональный прогноз\n"
            f"• 🔢 <b>Нумерология</b> — полный анализ чисел\n\n"
            f"📊 Бесплатно: {FREE_LIMIT} раскладов/день\n"
            f"💎 Премиум: без ограничений",
            reply_markup=main_keyboard,
            parse_mode="HTML"
        )

    async def check_limit(user_id: int):
        is_premium, req, _, _, _ = await get_user(user_id)
        if is_premium:
            return True, req
        if req >= FREE_LIMIT:
            return False, req
        return True, req

    @dp.message(F.text.in_(["⭐ Карта дня", "🔮 3 карты", "⚖️ 5 карт", "❤️ 7 карт", "⚔️ Кельтский крест"]))
    async def handle_spread(message: Message):
        user_id = message.from_user.id
        
        spread_map = {
            "⭐ Карта дня": "1_карта",
            "🔮 3 карты": "3_карты",
            "⚖️ 5 карт": "5_карт",
            "❤️ 7 карт": "7_карт",
            "⚔️ Кельтский крест": "10_карт"
        }
        spread_type = spread_map[message.text]
        
        allowed, req = await check_limit(user_id)
        if not allowed:
            await message.answer("❌ Лимит исчерпан. Купи премиум 💎")
            return
        
        spread = SPREADS[spread_type]
        wait_msg = await message.answer(f"{spread['emoji']} Делаю расклад <b>{spread['name']}</b>...", parse_mode="HTML")
        
        _, _, birth_date, gender, _ = await get_user(user_id)
        
        cards = make_spread(spread_type)
        interpretation = await generate_interpretation(cards, spread_type, birth_date, gender)
        await update_requests(user_id, req + 1)
        
        await wait_msg.delete()
        
        cards_list = []
        for i, card_info in enumerate(cards):
            status = "🔄" if card_info["is_reversed"] else "⬆️"
            
            suit_emoji = ""
            for suit, emoji in SUITS.items():
                if suit in card_info["name"]:
                    suit_emoji = emoji.split()[0]
                    break
            
            cards_list.append(f"{status} {spread['positions'][i]}: <b>{card_info['name']}</b> {suit_emoji}")
        
        advice = get_random_advice()
        
        response_text = (
            f"{spread['emoji']} <b>{spread['name']}</b>\n\n"
            f"<b>Выпавшие карты:</b>\n{chr(10).join(cards_list)}\n\n"
            f"<b>Толкование:</b>\n{interpretation}\n\n"
            f"💫 <b>Совет дня:</b>\n{advice}\n\n"
            f"📊 Использовано: {req + 1}/{FREE_LIMIT}"
        )
        
        await message.answer(response_text, parse_mode="HTML")

    @dp.message(F.text == "♈ Гороскоп")
    async def handle_horoscope(message: Message):
        user_id = message.from_user.id
        _, _, birth_date, gender, _ = await get_user(user_id)
        
        if not birth_date or not gender:
            await message.answer("❌ Пожалуйста, перезапустите бота командой /start")
            return
        
        wait_msg = await message.answer("♈ Составляю ваш персональный гороскоп...")
        horoscope_text = await generate_horoscope(birth_date, gender)
        await wait_msg.delete()
        
        try:
            day, month = map(int, birth_date.split('.'))
            zodiac = get_zodiac_sign(day, month)
            life_path = get_life_path_number(birth_date)
            gender_emoji = get_gender_emoji(gender)
        except:
            zodiac = "⭐"
            life_path = "?"
            gender_emoji = "🧑"
        
        await message.answer(
            f"♈ <b>Ваш гороскоп</b>\n\n"
            f"📅 Дата рождения: {birth_date}\n"
            f"⭐ Знак зодиака: {zodiac}\n"
            f"🔢 Число жизненного пути: {life_path}\n"
            f"👤 Пол: {gender_emoji} {gender}\n\n"
            f"{horoscope_text}\n\n"
            f"💫 {get_random_advice()}",
            parse_mode="HTML"
        )

    @dp.message(F.text == "🔢 Нумерология")
    async def handle_numerology(message: Message):
        user_id = message.from_user.id
        _, _, birth_date, gender, _ = await get_user(user_id)
        
        if not birth_date:
            await message.answer("❌ Пожалуйста, перезапустите бота командой /start")
            return
        
        try:
            day, month = map(int, birth_date.split('.'))
            
            life_path = get_life_path_number(birth_date)
            destiny = get_destiny_number(birth_date)
            soul_urge = get_soul_urge_number(birth_date)
            birth_day = get_birth_day_number(day)
            personality = get_personality_number(birth_date)
            zodiac = get_zodiac_sign(day, month)
            gender_emoji = get_gender_emoji(gender)
            
            numerology_text = f"""
    🔢 <b>Ваша нумерологическая карта</b>

    👤 {gender_emoji} {gender} | {zodiac}
    📅 Дата рождения: {birth_date}

    <u>Основные числа:</u>

    <b>1. Число жизненного пути: {life_path}</b>
    {get_numerology_interpretation(life_path)}
    Это ваше главное число, определяющее жизненный путь и предназначение.

    <b>2. Число судьбы: {destiny}</b>
    {get_numerology_interpretation(destiny)}
    Показывает, какие таланты и возможности даны вам от рождения.

    <b>3. Число душевного порыва: {soul_urge}</b>
    {get_numerology_interpretation(soul_urge)}
    Отражает ваши истинные желания и мотивации.

    <b>4. Число личности: {personality}</b>
    {get_numerology_interpretation(personality)}
    Как вас воспринимают окружающие.

    <b>5. Число дня рождения: {birth_day}</b>
    {get_numerology_interpretation(birth_day)}
    Ваш характер и особенности поведения.

    <u>Совет:</u>
    ✨ Используйте эти знания для понимания себя и своего пути.
    """
            
            await message.answer(numerology_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка в нумерологии: {e}")
            await message.answer("❌ Ошибка при расчете нумерологических данных. Попробуйте позже.")

    @dp.message()
    async def handle_user_data(message: Message):
        user_id = message.from_user.id
        step = user_state.get(user_id, {}).get("step")
        
        if step == "birth_date":
            text = message.text.strip()
            try:
                day, month = map(int, text.split('.'))
                if 1 <= day <= 31 and 1 <= month <= 12:
                    user_state[user_id] = {
                        "step": "gender",
                        "birth_date": text
                    }
                    await message.answer(
                        "✅ Дата рождения сохранена!\n\n"
                        "Теперь выберите ваш <b>пол</b>:",
                        parse_mode="HTML",
                        reply_markup=gender_keyboard
                    )
                else:
                    await message.answer("❌ Неверный формат. Введите дату в формате ДД.ММ (например, 15.06):")
            except:
                await message.answer("❌ Неверный формат. Введите дату в формате ДД.ММ (например, 15.06):")
        
        elif step == "gender":
            gender_map = {
                "👨 Мужской": "Мужской",
                "👩 Женский": "Женский"
            }
            
            if message.text in gender_map:
                gender = gender_map[message.text]
                birth_date = user_state[user_id]["birth_date"]
                
                await save_user_data(user_id, birth_date, gender)
                user_state[user_id] = {}
                
                await message.answer(
                    f"✅ Данные сохранены!\n"
                    f"📅 Дата рождения: {birth_date}\n"
                    f"👤 Пол: {gender}\n\n"
                    f"🔮 Добро пожаловать в мир Таро!",
                    reply_markup=main_keyboard
                )
                
                await show_main_menu(message)
            else:
                await message.answer(
                    "❌ Пожалуйста, выберите пол, используя кнопки ниже:",
                    reply_markup=gender_keyboard
                )

    @dp.message(F.text == "💎 Премиум")
    async def premium(message: Message):
        await message.answer(
            "💎 <b>Премиум режим</b>\n\n"
            "✔ Безлимитные расклады\n"
            "✔ Глубокие трактовки всех 78 карт\n"
            "✔ Перевернутые карты в раскладах\n"
            "✔ Персональный гороскоп с учетом пола\n"
            "✔ Полная нумерологическая карта\n"
            "✔ Приоритетные ответы от ИИ\n\n"
            "💰 Цена: 199₽/месяц\n"
            "👉 Для подключения напишите @your_support"
        )

# ===================== ГЛАВНАЯ ФУНКЦИЯ =====================
async def main():
    global TOKEN, OPENROUTER_API_KEY
    
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN не найден в переменных окружения!")
        return
    if not OPENROUTER_API_KEY:
        logger.error("❌ OPENROUTER_API_KEY не найден в переменных окружения!")
        return
    
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Регистрируем обработчики
    register_handlers(dp)
    
    await init_db()
    logger.info("🤖 Бот Таро запущен!")
    logger.info(f"📊 Доступно раскладов: {len(SPREADS)}")
    logger.info(f"🃏 Колода: {len(ALL_CARDS)} карт")
    logger.info(f"🔄 Перевернутые карты: {REVERSED_CHANCE*100}%")
    
    await dp.start_polling(bot, handle_signals=False)
if __name__ == "__main__":
    asyncio.run(main())
