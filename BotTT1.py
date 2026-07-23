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

# === ПРОВЕРКА ПОДПИСКИ ПО ОТДЕЛЬНОСТИ ===
def check_channel_sub(user_id: int) -> bool:
    """Проверка подписки на канал."""
    status_ok = ['creator', 'administrator', 'member']
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in status_ok
    except ApiTelegramException as e:
        print(f"[ERROR CHANNEL] Ошибка проверки: {e}")
        return False

def check_group_sub(user_id: int) -> bool:
    """Проверка подписки на группу."""
    status_ok = ['creator', 'administrator', 'member']
    try:
        group_member = bot.get_chat_member(GROUP_ID, user_id)
        return group_member.status in status_ok
    except ApiTelegramException as e:
        print(f"[ERROR GROUP] Ошибка проверки: {e}")
        return False

def build_dynamic_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """
    Формирует клавиатуру, скрывая кнопки каналов/групп,
    на которые пользователь УЖЕ подписался.
    """
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    is_sub_channel = check_channel_sub(user_id)
    is_sub_group = check_group_sub(user_id)
    
    # Показываем кнопку канала, ТОЛЬКО если пользователь НЕ подписан
    if not is_sub_channel:
        btn_channel = types.InlineKeyboardButton("📢 1. Подписаться на Канал", url="https://t.me/TikTokModCloudfreee")
        keyboard.add(btn_channel)
        
    # Показываем кнопку группы, ТОЛЬКО если пользователь НЕ подписан
    if not is_sub_group:
        btn_group = types.InlineKeyboardButton("💬 2. Подписаться на Группу", url="https://t.me/+MNIZMAO2r25iNjJi")
        keyboard.add(btn_group)
        
    # Кнопка проверки всегда присутствует
    btn_check = types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub")
    keyboard.add(btn_check)
    
    return keyboard

# Бодрящее приветственное сообщение
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
    user_id = message.from_user.id
    add_user(user_id)
    
    is_sub_channel = check_channel_sub(user_id)
    is_sub_group = check_group_sub(user_id)
    
    if is_sub_channel and is_sub_group:
        bot.send_message(message.chat.id, WELCOME_TEXT, parse_mode="Markdown")
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
    
    # Если подписан абсолютно на всё
    if is_sub_channel and is_sub_group:
        bot.answer_callback_query(call.id, "🎉 Все подписки подтверждены!", show_alert=True)
        try:
            bot.edit_message_text(
                WELCOME_TEXT,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="Markdown"
            )
        except ApiTelegramException:
            pass
    else:
        # Если подписан частично или никуда — обновляем клавиатуру (удаляя оформленные подписки)
        bot.answer_callback_query(call.id, "⚡️ Кнопки обновлены! Подпишитесь на оставшиеся ресурсы.", show_alert=False)
        try:
            new_markup = build_dynamic_keyboard(user_id)
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=new_markup
            )
        except ApiTelegramException:
            pass  # Вызывается, если состав кнопок не изменился

# === АДМИН ПАНЕЛЬ ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("📢 Рассылка всем", callback_data="admin_broadcast"))
    
    bot.send_message(
        message.chat.id,
        "⚙️ **Панель администратора**",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def start_broadcast_step(call):
    if call.from_user.id not in ADMIN_IDS:
        return
        
    msg = bot.send_message(
        call.message.chat.id,
        "📥 **Отправьте сообщение для рассылки.**\n\n"
        "Это может быть:\n"
        "• Обычный текст\n"
        "• Фото с описанием или без\n"
        "• Документ/файл с описанием или без\n\n"
        "_Для отмены отправьте /cancel_",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if message.text == "/cancel":
        bot.send_message(message.chat.id, "❌ Рассылка отменена.")
        return

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
        f"🚫 Заблокировали бота: {count_blocked}",
        parse_mode="Markdown"
    )

# === ЗАПУСК ===
if __name__ == "__main__":
    init_db()
    print("Бот успешно запущен...")
    bot.infinity_polling(skip_pending=True)