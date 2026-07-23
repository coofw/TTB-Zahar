import sqlite3
import time
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

# === НАСТРОЙКИ ===
TOKEN = "8817225650:AAE8uLOVH7w66-YB97zGGohfbLxeW0KiIHA"
ADMIN_IDS = [8484944484, 7543491052]

CHANNEL_USERNAME = "@TikTokModCloudfreee"
GROUP_ID = -1003637688275

bot = telebot.TeleBot(TOKEN)

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS last_broadcast (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            chat_id INTEGER,
            message_id INTEGER,
            text TEXT,
            photo_id TEXT,
            document_id TEXT,
            content_type TEXT
        )
    """)
    # Автоматически добавляем колонки, если таблица уже существовала со старой структурой
    try:
        cursor.execute("ALTER TABLE last_broadcast ADD COLUMN chat_id INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE last_broadcast ADD COLUMN message_id INTEGER")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE last_broadcast ADD COLUMN text TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE last_broadcast ADD COLUMN photo_id TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE last_broadcast ADD COLUMN document_id TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE last_broadcast ADD COLUMN content_type TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plugin_file (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            file_id TEXT,
            caption TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id: int):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def save_last_broadcast_data(message):
    content_type = message.content_type
    text = message.caption if message.caption else message.text
    photo_id = message.photo[-1].file_id if message.photo else None
    document_id = message.document.file_id if message.document else None

    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO last_broadcast (id, chat_id, message_id, text, photo_id, document_id, content_type)
        VALUES (1, ?, ?, ?, ?, ?, ?)
    """, (message.chat.id, message.message_id, text, photo_id, document_id, content_type))
    conn.commit()
    conn.close()

def get_last_broadcast():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, message_id, text, photo_id, document_id, content_type FROM last_broadcast WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row

def save_plugin_data(message):
    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id
        
    caption = message.caption if message.caption else message.text

    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO plugin_file (id, file_id, caption)
        VALUES (1, ?, ?)
    """, (file_id, caption))
    conn.commit()
    conn.close()

def get_plugin_data():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM plugin_file WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return row

def send_stored_content(chat_id, data):
    chat_id_src, message_id, text, photo_id, document_id, content_type = data
    
    if chat_id_src and message_id:
        try:
            bot.copy_message(chat_id=chat_id, from_chat_id=chat_id_src, message_id=message_id)
            return
        except Exception:
            pass 

    try:
        if content_type == 'photo' and photo_id:
            bot.send_photo(chat_id, photo_id, caption=text, parse_mode="Markdown")
        elif content_type == 'document' and document_id:
            bot.send_document(chat_id, document_id, caption=text, parse_mode="Markdown")
        elif text:
            bot.send_message(chat_id, text, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "📭 В боте пока не было ни одной рассылки.")
    except Exception as e:
        print(f"[ERROR SEND CONTENT] {e}")
        bot.send_message(chat_id, "📭 В боте пока не было ни одной рассылки.")

# === КЛАВИАТУРЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ===
def get_user_main_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("📬 Получить последнюю рассылку (мод)"))
    keyboard.add(types.KeyboardButton("📦 Получить плагин"))
    return keyboard

# === ПРОВЕРКА ПОДПИСКИ ПО ОТДЕЛЬНОСТИ ===
def check_channel_sub(user_id: int) -> bool:
    status_ok = ['creator', 'administrator', 'member']
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in status_ok
    except ApiTelegramException as e:
        print(f"[ERROR CHANNEL] Ошибка проверки: {e}")
        return False

def check_group_sub(user_id: int) -> bool:
    status_ok = ['creator', 'administrator', 'member']
    try:
        group_member = bot.get_chat_member(GROUP_ID, user_id)
        return group_member.status in status_ok
    except ApiTelegramException as e:
        print(f"[ERROR GROUP] Ошибка проверки: {e}")
        return False

def build_dynamic_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    is_sub_channel = check_channel_sub(user_id)
    is_sub_group = check_group_sub(user_id)
    
    if not is_sub_channel:
        keyboard.add(types.InlineKeyboardButton("📢 1. Подписаться на Канал", url="https://t.me/TikTokModCloudfreee"))
    if not is_sub_group:
        keyboard.add(types.InlineKeyboardButton("💬 2. Подписаться на Группу", url="https://t.me/+MNIZMAO2r25iNjJi"))
        
    keyboard.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub"))
    return keyboard

WELCOME_TEXT = (
    "🚀 **Привет-привет! Добро пожаловать на борт!** 🔥⚡️\n\n"
    "🎉 *Огромное спасибо*, что подписался на наш канал и группу!\n"
    "Ты делаешь этот проект лучше! 💪😎\n\n"
    "✨ **Здесь тебя ждёт всё самое свежее:**\n"
    "🔹 Мгновенные обновления и релизы 📦\n"
    "🔹 Горячие новости и эксклюзивная информация 📰🔥\n"
    "🔹 Полезные анонсы и важные объявления 🔔\n\n"
    "💬 _Оставайся с нами на связи и не отключай уведомления, дальше — больше!_ 🚀⚡️"
)

# === ОБРАБОТЧИКИ КОМАНД ===
@bot.message_handler(commands=['start'])
def start_cmd(message):
    # Игнорируем команду /start в группах и каналах
    if message.chat.type != 'private':
        return

    user_id = message.from_user.id
    add_user(user_id)
    
    is_sub_channel = check_channel_sub(user_id)
    is_sub_group = check_group_sub(user_id)
    
    if is_sub_channel and is_sub_group:
        bot.send_message(
            message.chat.id, 
            WELCOME_TEXT, 
            parse_mode="Markdown", 
            reply_markup=get_user_main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "👋 **Привет!** Чтобы получить доступ, подпишись на наши ресурсы ниже:",
            parse_mode="Markdown",
            reply_markup=build_dynamic_keyboard(user_id)
        )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    user_id = call.from_user.id
    is_sub_channel = check_channel_sub(user_id)
    is_sub_group = check_group_sub(user_id)
    
    if is_sub_channel and is_sub_group:
        bot.answer_callback_query(call.id, "🎉 Все подписки подтверждены!", show_alert=True)
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        except ApiTelegramException:
            pass
        bot.send_message(
            call.message.chat.id,
            WELCOME_TEXT,
            parse_mode="Markdown",
            reply_markup=get_user_main_keyboard()
        )
    else:
        bot.answer_callback_query(call.id, "⚡️ Кнопки обновлены! Подпишитесь на оставшиеся ресурсы.", show_alert=False)
        try:
            new_markup = build_dynamic_keyboard(user_id)
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=new_markup
            )
        except ApiTelegramException:
            pass

# === ОБРАБОТЧИКИ КНОПОК ПОЛЬЗОВАТЕЛЯ ===
@bot.message_handler(func=lambda message: message.text == "📬 Получить последнюю рассылку (мод)")
def handle_get_last_broadcast(message):
    user_id = message.from_user.id
    add_user(user_id)

    if not (check_channel_sub(user_id) and check_group_sub(user_id)):
        bot.send_message(
            message.chat.id,
            "⚠️ Чтобы просматривать рассылку, подпишитесь на наши ресурсы!",
            reply_markup=build_dynamic_keyboard(user_id)
        )
        return

    last_bc = get_last_broadcast()
    if not last_bc or not any(last_bc):
        bot.send_message(message.chat.id, "📭 В боте пока не было ни одной рассылки.")
        return

    send_stored_content(message.chat.id, last_bc)

@bot.message_handler(func=lambda message: message.text == "📦 Получить плагин")
def handle_get_plugin(message):
    user_id = message.from_user.id
    add_user(user_id)

    if not (check_channel_sub(user_id) and check_group_sub(user_id)):
        bot.send_message(
            message.chat.id,
            "⚠️ Чтобы получить плагин, подпишитесь на наши ресурсы!",
            reply_markup=build_dynamic_keyboard(user_id)
        )
        return

    plugin = get_plugin_data()
    if not plugin or not plugin[0]:
        bot.send_message(message.chat.id, "📭 Версия плагина еще не загружена администратором.")
        return

    file_id, caption = plugin
    try:
        bot.send_document(message.chat.id, file_id, caption=caption, parse_mode="Markdown")
    except Exception:
        try:
            bot.send_photo(message.chat.id, file_id, caption=caption, parse_mode="Markdown")
        except Exception as e:
            print(f"[ERROR PLUGIN] {e}")
            bot.send_message(message.chat.id, "❌ Не удалось отправить файл плагина.")

# === АДМИН ПАНЕЛЬ ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("✏️ Изменить мод", callback_data="admin_update_last"),
        types.InlineKeyboardButton("🔄 Обновить версию плагина", callback_data="admin_update_plugin")
    )
    
    bot.send_message(
        message.chat.id,
        "⚙️ **Панель администратора**",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# 1. Сделать рассылку (и обновить мод)
@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def start_broadcast_step(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    msg = bot.send_message(
        call.message.chat.id,
        "📥 **Отправьте сообщение для рассылки всем (оно также обновит кнопку мода):**\n\n"
        "Это может быть текст, фото или документ.\n\n"
        "_Для отмены отправьте /cancel_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.text and message.text.lower() == "/cancel":
        bot.send_message(message.chat.id, "❌ Рассылка отменена.")
        return

    save_last_broadcast_data(message)

    users = get_all_users()
    count_success = 0
    count_blocked = 0

    bot.send_message(message.chat.id, f"🚀 Начинаю рассылку для {len(users)} пользователей...")

    for user_id in users:
        try:
            bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            count_success += 1
            time.sleep(0.04) 
        except ApiTelegramException as e:
            if e.error_code == 403:
                count_blocked += 1
            elif e.error_code == 429:
                retry_after = e.result_json.get('parameters', {}).get('retry_after', 5)
                time.sleep(retry_after)
                try:
                    bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
                    count_success += 1
                except Exception:
                    pass
            else:
                print(f"[BROADCAST ERROR] Пользователь {user_id}: {e}")

    bot.send_message(
        message.chat.id,
        f"📊 **Результаты рассылки:**\n\n"
        f"✅ Успешно доставлено: {count_success}\n"
        f"🚫 Заблокировали бота: {count_blocked}\n"
        f"📌 *Рассылка завершена, содержимое кнопки 'Последняя рассылка (мод)' обновлено!*",
        parse_mode="Markdown"
    )

# 2. Изменить мод (без рассылки всем)
@bot.callback_query_handler(func=lambda call: call.data == "admin_update_last")
def start_update_last_step(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    msg = bot.send_message(
        call.message.chat.id,
        "📥 **Отправьте новый контент для кнопки 'Получить последнюю рассылку (мод)'.**\n"
        "_(Сообщение НЕ будет разослано автоматически)_\n\n"
        "_Для отмены отправьте /cancel_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_update_last)

def process_update_last(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.text and message.text.lower() == "/cancel":
        bot.send_message(message.chat.id, "❌ Действие отменено.")
        return

    save_last_broadcast_data(message)

    bot.send_message(
        message.chat.id,
        "✅ **Мод успешно обновлен!**\nТеперь пользователи получат его при нажатии на соответствующую кнопку.",
        parse_mode="Markdown"
    )

# 3. Обновить версию плагина
@bot.callback_query_handler(func=lambda call: call.data == "admin_update_plugin")
def start_update_plugin_step(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    msg = bot.send_message(
        call.message.chat.id,
        "📥 **Отправьте файл новой версии плагина** (документом или файлом, можно с описанием):\n\n"
        "_Для отмены отправьте /cancel_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_update_plugin)

def process_update_plugin(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.text and message.text.lower() == "/cancel":
        bot.send_message(message.chat.id, "❌ Действие отменено.")
        return

    if not message.document and not message.photo:
        bot.send_message(message.chat.id, "⚠️ Пожалуйста, отправьте именно файл/документ или фото с плагином. Попробуйте еще раз через /admin.")
        return

    save_plugin_data(message)

    bot.send_message(
        message.chat.id,
        "✅ **Версия плагина успешно обновлена!**\nТеперь пользователи могут получить его через кнопку.",
        parse_mode="Markdown"
    )

# === ЗАПУСК ===
if __name__ == "__main__":
    init_db()
    print("Бот успешно запущен...")
    bot.infinity_polling(skip_pending=True)