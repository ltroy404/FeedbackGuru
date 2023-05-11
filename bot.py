from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
import requests
import sqlite3


API_SERVER_URL = "http://localhost:12345"
TOKEN = "6194979947:AAGcZCLLZ-UB96dzxwBywAH3aAaPTEsaB5k"


def create_table_if_not_exists():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Создание таблицы
    c.execute('''
    CREATE TABLE IF NOT EXISTS users
    (user_id INTEGER PRIMARY KEY,
    api_key TEXT);
    ''')


    conn.commit()
    conn.close()

def add_api_key(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    api_key = update.message.text

    if context.user_data.get('state') != 'adding_api_key':
        handle_unexpected_text(update, context)
        return

    context.user_data['api_key'] = api_key
    context.user_data['state'] = None

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Проверяем, существует ли уже пользователь в базе данных
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    # Если пользователь существует, обновляем его API ключ. В противном случае, добавляем нового пользователя.
    if data is None:
        c.execute("INSERT INTO users VALUES (?,?)", (user_id, api_key))
    else:
        c.execute("UPDATE users SET api_key = ? WHERE user_id = ?", (api_key, user_id))

    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
        [InlineKeyboardButton("🔙Назад", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("API ключ успешно добавлен!✅", reply_markup=reply_markup)

def remove_api_key(update: Update, context: CallbackContext):
    user_id = update.callback_query.from_user.id
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM api_keys WHERE user_id = {user_id}")
        conn.commit()
    
    keyboard = [
        [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
        [InlineKeyboardButton("🔙Назад", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.edit_message_text(text="API ключ успешно удален!✅", reply_markup=reply_markup)

def get_api_key(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Получение API ключа пользователя
    c.execute("SELECT api_key FROM users WHERE user_id=?", (user_id,))
    api_key = c.fetchone()  # Извлечение API ключа из результата запроса
    conn.close()
    return api_key[0] if api_key else None

def print_unanswered_feedbacks(user_id, context):
    try:
    
        api_key = get_api_key(user_id)
        feedbacks = get_unanswered_feedbacks(context, api_key)

        if feedbacks and not feedbacks.get("error"):
            print("Неотвеченные отзывы:")
            for feedback in feedbacks["data"]["feedbacks"]:
                print(feedback)
        else:
            print("Ошибка при получении данных с сервера:", feedbacks.get("message"))
    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")

def get_unanswered_feedbacks(context, api_key, take=10, skip=0):
    try:
        if not api_key:
            return {"error": True, "message": "Отсутствует API для запроса отзывов. Пожалуйста, добавьте ключ."}
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(f"{API_SERVER_URL}/api/v1/feedbacks/unanswered", params={"take": take, "skip": skip}, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": True, "message": f"Error fetching data from server. Status code: {response.status_code}, Response: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": True, "message": f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw"}

def send_response_to_review(api_key, review_id, response_text):
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.post(f"{API_SERVER_URL}/api/v1/feedbacks/{review_id}/reply", json={"response": response_text}, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": True, "message": f"Ошибка отправки ответа на сервер. Пожалуйста, свяжитесь с поддержкой: @ltroy_sw Status code: {response.status_code}, Response: {response.text}"}
    except Exception as e:
        return {"error": True, "message": f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw"}

def start(update: Update, context: CallbackContext):
    try:
        keyboard = [
            [InlineKeyboardButton("⚙Настройки", callback_data="settings")],
            [InlineKeyboardButton("📊Неотвеченные отзывы", callback_data='unanswered_feedbacks')],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            update.callback_query.edit_message_text('Привет! Я бот проекта FeedBackGuru. Выберите действие:', reply_markup=reply_markup)
        else:
            update.message.reply_text('Привет! Я бот проекта FeedBackGuru. Выберите действие:', reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")
        if update.callback_query:
            update.callback_query.edit_message_text("Произошла ошибка, пожалуйста, свяжитесь с поддержкой: @ltroy_sw❌")
        else:
            update.message.reply_text("Произошла ошибка, пожалуйста, свяжитесь с поддержкой: @ltroy_sw❌")

def send_message_to_server(prompt):
    try:
        response = requests.post(f"{API_SERVER_URL}/api/v1/generate_response", json={"prompt": prompt})
        if response.status_code == 200:
            return response.json()["response"]
        else:
            print(f"Ошибка сервера: {response.status_code}, {response.text}")
            return "Ошибка при обработке запроса на сервере"
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw"

def button_callback(update, context):
    try:
        query = update.callback_query
        query.answer()
        user_id = query.from_user.id
        context.user_data['api_key'] = get_api_key(user_id)

        keyboard = []

        if query.data == 'settings':
            keyboard = [
                [InlineKeyboardButton("🔐Добавить API Wildberries", callback_data="add_wildberries_api_key")],
                [InlineKeyboardButton("🗑Удалить API Wildberries", callback_data="remove_api_key")],
                [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text="⚙Настройки:", reply_markup=reply_markup)

        elif query.data == 'remove_api_key':
            remove_api_key(update, context)
            query.edit_message_text(text="API ключ успешно удален!✅")

        elif query.data == 'back_to_main_menu':
            start(update, context)

        if query.data == 'add_wildberries_api_key':
            context.user_data['state'] = 'adding_api_key'
            keyboard = [
                [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                [InlineKeyboardButton("🔙Назад", callback_data="settings")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text="Отправьте свой ключ Wildberries", reply_markup=reply_markup)


        if query.data == 'unanswered_feedbacks':
            feedbacks = get_unanswered_feedbacks(context, context.user_data.get('api_key'))
            if feedbacks and not feedbacks.get("error"):
                if feedbacks["data"]["feedbacks"]:
                    for feedback in feedbacks["data"]["feedbacks"]:
                        context.user_data['feedback_text'] = feedback["text"]
                        keyboard = [
                            [InlineKeyboardButton("📝Сгенерировать ответ", callback_data=f'generate_response:{feedback["id"]}'),
                            InlineKeyboardButton("✏️Ответить вручную", callback_data=f'manually_answer:{feedback["id"]}'),
                            InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        update.callback_query.message.reply_text(feedback["text"], reply_markup=reply_markup)

                else:
                    update.callback_query.message.reply_text("Нет неотвеченных отзывов🔊")
            else:
                query.edit_message_text(text=feedbacks.get("message") + "❌")

        elif query.data.startswith('generate_response:'):
            feedback_id = query.data.split(':')[1]
            prompt = context.user_data.get('feedback_text')
            generated_response = send_message_to_server(prompt)
            keyboard = [
                [InlineKeyboardButton("✅Опубликовать ответ", callback_data=f'publish_response:{feedback_id}')],
                [InlineKeyboardButton("✉️Исправить и опубликовать", callback_data=f'correct_and_publish_response:{feedback_id}')],
                [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                [InlineKeyboardButton("🔙Назад", callback_data=f'unanswered_feedbacks')],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text=generated_response, reply_markup=reply_markup)

        elif query.data.startswith('publish_response:'):
            feedback_id = query.data.split(':')[1]
            response_text = query.message.text
            api_key = context.user_data.get('api_key')
            result = send_response_to_review(api_key, feedback_id, response_text)

            if result.get("error"):
                query.edit_message_text(text=f"Ошибка при отправке ответа: {result.get('message')}❌")
            else:
                keyboard = [
                    [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                ]
                query.edit_message_text(text="Ответ опубликован✅", reply_markup=reply_markup)

        elif query.data.startswith('correct_and_publish_response:'):
            feedback_id = query.data.split(':')[1]
            context.user_data['current_feedback_id'] = feedback_id
            context.user_data['state'] = 'correcting_response'
            keyboard = [
                [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                [InlineKeyboardButton("🔙Назад", callback_data=f'generate_response:{feedback_id}')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text="Введите исправленный ответ", reply_markup=reply_markup)

        elif query.data == 'back_to_feedbacks':
            feedbacks = get_unanswered_feedbacks(context, context.user_data.get('api_key'))
            if feedbacks and not feedbacks.get("error"):
                if feedbacks["data"]["feedbacks"]:
                    for feedback in feedbacks["data"]["feedbacks"]:
                        context.user_data['feedback_text'] = feedback["text"]
                        keyboard = [[InlineKeyboardButton("📝Сгенерировать ответ", callback_data=f'generate_response:{feedback["id"]}')]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        update.callback_query.message.reply_text(feedback["text"], reply_markup=reply_markup)
                else:
                    update.callback_query.message.reply_text("Нет неотвеченных отзывов🔊")
            else:
                query.edit_message_text(text=feedbacks.get("message") + "❌")
        elif query.data.startswith('manually_answer:'):
            feedback_id = query.data.split(':')[1]
            context.user_data['current_feedback_id'] = feedback_id
            context.user_data['state'] = 'manually_answering'
            keyboard = [
                [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                [InlineKeyboardButton("🔙Назад", callback_data=f'unanswered_feedbacks')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text="Пришлите ответ на отзыв", reply_markup=reply_markup)

    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")
        query.edit_message_text("Произошла ошибка, пожалуйста, свяжитесь с поддержкой: @ltroy_sw❌")

def send_edited_response_to_review(update: Update, context: CallbackContext):
    if context.user_data.get('state') != 'editing_response':
        handle_unexpected_text(update, context)
        return

    edited_response = update.message.text
    feedback_id = context.user_data.get('current_feedback_id')
    api_key = get_api_key(update.message.from_user.id)  # Получение API ключа
    result = send_response_to_review(api_key, feedback_id, edited_response)

    if result.get("error"):
        update.message.reply_text(f"Ошибка при отправке исправленного ответа: {result.get('message')}")
    else:
        update.message.reply_text("Исправленный ответ опубликован")
        context.user_data['state'] = None

def handle_unexpected_text(update: Update, context: CallbackContext):
    if context.user_data.get('state') == 'editing_response':
        send_edited_response_to_review(update, context)
    if context.user_data.get('state') == 'manually_answering':
        send_edited_response_to_review(update, context)
    else:
        update.message.reply_text("Пожалуйста, нажмите на соответствующую функцию, чтобы клиент обработал сообщение. Если возникла проблема или по любым вопросам пишите в поддержку: @ltroy_sw")

def main():
    create_table_if_not_exists() 
    
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_callback))
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private & ~Filters.command & Filters.update.message, add_api_key))
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private & ~Filters.command & Filters.update.edited_message, handle_unexpected_text))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_unexpected_text))
    dp.add_handler(CallbackQueryHandler(remove_api_key, pattern='^remove_api$'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()