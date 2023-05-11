import logging
from telegram import Update
import socket
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler
import requests

API_SERVER_URL = "http://localhost:12345"
TOKEN = "6194979947:AAGcZCLLZ-UB96dzxwBywAH3aAaPTEsaB5k"

def add_api_key(update: Update, context: CallbackContext):
    if context.user_data.get('state') != 'adding_api_key':
        handle_unexpected_text(update, context)
        return

    api_key = update.message.text
    context.user_data['api_key'] = api_key
    context.user_data['state'] = None
    update.message.reply_text("API ключ успешно добавлен!")


def print_unanswered_feedbacks(context):
    try:
        feedbacks = get_unanswered_feedbacks(context)

        if feedbacks and not feedbacks.get("error"):
            print("Неотвеченные отзывы:")
            for feedback in feedbacks["data"]["feedbacks"]:
                print(feedback)
        else:
            print("Ошибка при получении данных с сервера:", feedbacks.get("message"))
    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")


def get_unanswered_feedbacks(context, take=10, skip=0):
    try:
        api_key = context.user_data.get('api_key')
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
            [InlineKeyboardButton("Настройки", callback_data="settings")],
            [InlineKeyboardButton("Неотвеченные отзывы", callback_data='unanswered_feedbacks')],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Привет! Я бот проекта FeedBackGuru. Выберите действие:', reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")
        update.message.reply_text("Произошла ошибка, пожалуйста, свяжитесь с поддержкой: @ltroy_sw")



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

        keyboard = []

        if query.data == 'settings':
            keyboard = [
                [InlineKeyboardButton("Добавить API Wildberries", callback_data="add_wildberries_api_key")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text="Настройки:", reply_markup=reply_markup)

        if query.data == 'add_wildberries_api_key':
            context.user_data['state'] = 'adding_api_key'
            query.edit_message_text(text="Отправьте свой ключ Wildberries")

        if query.data == 'unanswered_feedbacks':
            feedbacks = get_unanswered_feedbacks(context)
            if feedbacks and not feedbacks.get("error"):
                if feedbacks["data"]["feedbacks"]:
                    for feedback in feedbacks["data"]["feedbacks"]:
                        context.user_data['feedback_text'] = feedback["text"]
                        keyboard = [[InlineKeyboardButton("Сгенерировать ответ", callback_data=f'generate_response:{feedback["id"]}')]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        update.callback_query.message.reply_text(feedback["text"], reply_markup=reply_markup)
                else:
                    update.callback_query.message.reply_text("Нет неотвеченных отзывов")
            else:
                query.edit_message_text(text=feedbacks.get("message"))

        elif query.data.startswith('generate_response:'):
            feedback_id = query.data.split(':')[1]
            prompt = context.user_data.get('feedback_text')
            generated_response = send_message_to_server(prompt)
            keyboard = [
                [InlineKeyboardButton("Опубликовать ответ", callback_data=f'publish_response:{feedback_id}')],
                [InlineKeyboardButton("Исправить и опубликовать", callback_data=f'correct_and_publish_response:{feedback_id}')],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(text=generated_response, reply_markup=reply_markup)

        elif query.data.startswith('publish_response:'):
            feedback_id = query.data.split(':')[1]
            response_text = query.message.text
            api_key = context.user_data.get('api_key')
            result = send_response_to_review(api_key, feedback_id, response_text)

            if result.get("error"):
                query.edit_message_text(text=f"Ошибка при отправке ответа: {result.get('message')}")
            else:
                query.edit_message_text(text="Ответ опубликован")


        elif query.data.startswith('correct_and_publish_response:'):
            feedback_id = query.data.split(':')[1]
            context.user_data['current_feedback_id'] = feedback_id
            context.user_data['state'] = 'editing_response'
            query.edit_message_text(text="Пожалуйста, внесите изменения в сгенерированный ответ и отправьте его обратно.")

    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")
        query.edit_message_text("Произошла ошибка, пожалуйста, свяжитесь с поддержкой: @ltroy_sw")


def send_edited_response_to_review(update: Update, context: CallbackContext):
    if context.user_data.get('state') != 'editing_response':
        handle_unexpected_text(update, context)
        return

    edited_response = update.message.text
    feedback_id = context.user_data.get('current_feedback_id')
    api_key = context.user_data.get('api_key')
    result = send_response_to_review(api_key, feedback_id, edited_response)

    if result.get("error"):
        update.message.reply_text(f"Ошибка при отправке исправленного ответа: {result.get('message')}")
    else:
        update.message.reply_text("Исправленный ответ опубликован")
        context.user_data['state'] = None

def handle_unexpected_text(update: Update, context: CallbackContext):
    if context.user_data.get('state') == 'editing_response':
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

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()