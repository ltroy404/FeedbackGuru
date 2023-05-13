from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
import requests
import sqlite3


API_SERVER_URL = "http://localhost:12345"
TOKEN = "6194979947:AAEAzlIdQd9w_2abq7ixFBk7o3s1kiw8p9Q"


def add_api_key(update: Update, context: CallbackContext):
    try:
        api_key = update.message.text
        user_id = update.message.chat_id

        response = requests.post(f"{API_SERVER_URL}/api/v1/add_api_key", json={"api_key": api_key, "user_id": user_id})

        if response.status_code == 200:
            keyboard = [
            [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
            [InlineKeyboardButton("🔙Назад", callback_data="settings")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text("API ключ успешно добавлен!✅", reply_markup=reply_markup)
    except Exception as e:
        keyboard = [
            [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
            [InlineKeyboardButton("🔙Назад", callback_data="settings")],
            ]
        update.message.reply_text (f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw", reply_markup=reply_markup)

def remove_api_key(update: Update, context: CallbackContext):
    try:
        user_id = update.callback_query.from_user.id

        # Запрос к серверу для удаления API-ключа
        response = requests.post(f"{API_SERVER_URL}/api/v1/remove_api_key", json={"user_id": user_id})

        keyboard = [
            [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
            [InlineKeyboardButton("🔙Назад", callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Если запрос был успешным
        if response.status_code == 200:
            update.callback_query.edit_message_text(text="API ключ успешно удален!✅", reply_markup=reply_markup)
        else:
            update.callback_query.edit_message_text(text="Произошла ошибка при удалении API-ключа.", reply_markup=reply_markup)

    except Exception as e:
        update.callback_query.edit_message_text (f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw", reply_markup=reply_markup)

def print_unanswered_feedbacks(user_id, context):
    try:
        feedbacks = get_unanswered_feedbacks(context, user_id)
        if feedbacks and not feedbacks.get("error"):
            print("Неотвеченные отзывы:")
            for feedback in feedbacks["data"]["feedbacks"]:
                print(feedback)
        else:
            print("Ошибка при получении данных с сервера:", feedbacks.get("message"))
    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")

def get_unanswered_feedbacks(context, user_id, take=10, skip=0):
    try:
        headers = {"user_id": str(user_id)}
        response = requests.get(f"{API_SERVER_URL}/api/v1/feedbacks/unanswered", params={"take": take, "skip": skip}, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": True, "message": f"Error fetching data from server. Status code: {response.status_code}, Response: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": True, "message": f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw"}

def send_response_to_review(user_id, review_id, response_text):
    try:
        headers = {"user_id": str(user_id)}
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
            keyboard = [  
                    [InlineKeyboardButton("🔐Добавить API Wildberries", callback_data="add_wildberries_api_key")],
                    [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text="API ключ успешно удален!✅", reply_markup=reply_markup)

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
            feedbacks = get_unanswered_feedbacks(context, user_id)
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
                    keyboard = [
                        [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    update.callback_query.message.reply_text("Нет неотвеченных отзывов🔊", reply_markup=reply_markup)
            else:
                keyboard = [
                    [InlineKeyboardButton("🔐Добавить API Wildberries", callback_data="add_wildberries_api_key")],
                    [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(text=feedbacks.get("message") + "❌", reply_markup=reply_markup)

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
            result = send_response_to_review(user_id, feedback_id, response_text)


            if result.get("error"):
                keyboard = [
                    [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(text=f"Ошибка при отправке ответа: {result.get('message')}❌", reply_markup=reply_markup)
            else:
                keyboard = [
                    [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
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
            feedbacks = get_unanswered_feedbacks(context, user_id)
            if feedbacks and not feedbacks.get("error"):
                if feedbacks["data"]["feedbacks"]:
                    for feedback in feedbacks["data"]["feedbacks"]:
                        context.user_data['feedback_text'] = feedback["text"]
                        keyboard = [
                            [InlineKeyboardButton("📝Сгенерировать ответ", callback_data=f'generate_response:{feedback["id"]}')],
                            [InlineKeyboardButton("✏️Ответить вручную", callback_data=f'manually_answer:{feedback["id"]}')],
                            [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        update.callback_query.message.reply_text(feedback["text"], reply_markup=reply_markup)
                else:
                    keyboard = [
                        [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    update.callback_query.message.reply_text("Нет неотвеченных отзывов🔊", reply_markup=reply_markup)
            else:
                keyboard = [
                    [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(text=feedbacks.get("message") + "❌", reply_markup=reply_markup)

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
        query.edit_message_text(f"Произошла ошибка:{str(e)}, пожалуйста, свяжитесь с поддержкой: @ltroy_sw❌")

def send_edited_response_to_review(update: Update, context: CallbackContext):
    if context.user_data.get('state') != 'correcting_response' and context.user_data.get('state') != 'manually_answering':
        handle_unexpected_text(update, context)
        return

    edited_response = update.message.text
    feedback_id = context.user_data.get('current_feedback_id')
    user_id = str(update.message.from_user.id)  
    result = send_response_to_review(user_id, feedback_id, edited_response)

    if result.get("error"):
        update.message.reply_text(f"Ошибка при отправке исправленного ответа: {result.get('message')}")
    else:
        keyboard = [
                    [InlineKeyboardButton("ℹ️Главное меню", callback_data="back_to_main_menu")],
                ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Ответ опубликован✅", reply_markup=reply_markup)
        context.user_data['state'] = None

def handle_unexpected_text(update: Update, context: CallbackContext):
    if context.user_data.get('state') == 'correcting_response':
        send_edited_response_to_review(update, context)
    elif context.user_data.get('state') == 'manually_answering':
        send_edited_response_to_review(update, context)
    else:
        update.message.reply_text("Пожалуйста, нажмите на соответствующую функцию, чтобы клиент обработал сообщение. Если возникла проблема или по любым вопросам пишите в поддержку: @ltroy_sw")

def main():
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