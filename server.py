import socket
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import sqlite3

app = Flask(__name__)
CORS(app)

WB_API_URL = "https://feedbacks-api.wildberries.ru"
openai.api_key = "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"


#БЛОК РАБОТЫ С БД
def create_table_if_not_exists():#создаёт БД
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Создание таблицы
    c.execute('''
    CREATE TABLE IF NOT EXISTS users
    (user_id INTEGER PRIMARY KEY,
    api_key TEXT,
    access INTEGER DEFAULT 0);  
    ''')

    conn.commit()
    conn.close()

def check_access(user_id):#проверяет доступ
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Запрос на получение значения 'access' для данного user_id
    c.execute("SELECT access FROM users WHERE user_id = ?", (user_id,))

    result = c.fetchone()  # Получение результата запроса
    conn.close()

    if result is None:
        return False  # Если результат None, значит, такого пользователя нет в базе данных

    return bool(result[0])  # Преобразуем результат в bool и возвращаем


def give_access(user_id: int):  # предоставляет пользователю доступ
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Обновление статуса доступа на True
    c.execute("UPDATE users SET access = 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def revoke_access(user_id: int):  # отзывает доступ у пользователя
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Обновление статуса доступа на False
    c.execute("UPDATE users SET access = 0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_api_key(user_id: int):  # извлекает API WB из БД
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Получение API ключа пользователя
    c.execute("SELECT api_key FROM users WHERE user_id=?", (user_id,))
    api_key = c.fetchone()  # Извлечение API ключа из результата запроса
    conn.close()

    if api_key:
        return api_key[0]
    else:
        return None

@app.route("/api/v1/add_api_key", methods=["POST"])
def receive_api_key():#принимает API WB и вызывает add_api_key
    api_key = request.json.get("api_key")
    user_id = request.json.get("user_id")
    if not api_key or not user_id:
        return jsonify({"error": True, "message": "API-ключ и user_id обязательны для передачи"}), 400

    add_api_key(user_id, api_key)

    return jsonify({"message": "API-ключ успешно получен"})

def add_api_key(user_id: int, api_key: str):  # добавляет API WB в БД
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Проверка, есть ли уже такой пользователь
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()
    if data is None:
        c.execute("INSERT INTO users (user_id, api_key, access) VALUES (?,?,?)", (user_id, api_key, False))
        print(f'API-ключ {api_key} добавлен в базу данных для пользователя {user_id} с доступом по умолчанию (False)')
    else:
        # Получаем текущий статус доступа
        current_access = check_access(user_id)
        # Преобразуем булевое значение в целое число
        current_access = 1 if current_access else 0
        c.execute("UPDATE users SET api_key=?, access=? WHERE user_id=?", (api_key, current_access, user_id))
        print(f'API-ключ {api_key} обновлен в базе данных для пользователя {user_id} и текущий статус доступа сохранен')

    conn.commit()
    conn.close()

@app.route("/api/v1/remove_api_key", methods=["POST"])
def receive_user_id_for_removal():#принимает user_id и вызывает remove_api_key
    user_id = request.json.get("user_id")
    if not user_id:
        return jsonify({"error": True, "message": "User_id is required"}), 400

    remove_api_key(user_id)

    return jsonify({"message": "API key removed successfully"})

def remove_api_key(user_id: int):  # Удаляет API WB из БД
    current_access = check_access(user_id)  # Проверяем текущий статус доступа
    conn = sqlite3.connect('users.db')  
    c = conn.cursor() 

    # Если доступ есть, то удаляем API ключ, но оставляем запись пользователя с его текущим статусом доступа
    if current_access:
        c.execute("UPDATE users SET api_key=NULL WHERE user_id=?", (user_id,))
    else:
        # Если доступа нет, то удаляем всю запись о пользователе
        c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit() 
    conn.close()  


#БЛОК РАБОТЫ С WB
@app.route("/api/v1/feedbacks/unanswered", methods=["GET"])
def get_unanswered_feedbacks():  # Обрабатывает запрос на получение непрошедших проверку отзывов от клиента.
    try:
        user_id = request.headers.get("user_id")
        if not user_id:
            return jsonify({"error": True, "message": "User_id не предоставлен"}), 400

        api_key = get_api_key(user_id)  # Извлечение API-ключа из базы данных
        if not api_key:
            return jsonify({"error": True, "message": "API-ключ не найден для данного user_id"}), 400

        # Проверяем доступ пользователя
        if not check_access(user_id):
            return jsonify({"error": True, "message": "Где деньги, Лебовски?"}), 403

        take = request.args.get("take", 10)
        skip = request.args.get("skip", 0)

        response = fetch_unanswered_feedbacks(api_key, take, skip)
        if response:
            return jsonify(response)
        else:
            return jsonify({"error": True, "message": "Ошибка получения данных от Wildberries API"}), 500
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return jsonify({"error": True, "message": "Произошла ошибка, пожалуйста, свяжитесь с поддержкой"}), 500

def fetch_unanswered_feedbacks(api_key, take, skip):  # Получает непроверенные отзывы с использованием API WB и возвращает результат.
    headers = {"Authorization": api_key, "accept": "application/json"}
    params = {"take": take, "skip": skip, "answered": "false", "isAnswered": "false"}
    response = requests.get(f"{WB_API_URL}/api/v1/feedbacks", headers=headers, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data from Wildberries API. Status code: {response.status_code}, Response: {response.text}")
        return None

@app.route("/api/v1/feedbacks/<review_id>/reply", methods=["POST"])
def post_feedback_reply(review_id):#Обрабатывает запрос на отправку ответа на отзыв и вызывает reply_to_review.
    user_id = request.headers.get("user_id")
    if not user_id:
        return jsonify({"error": True, "message": "User_id не предоставлен"}), 400

    api_key = get_api_key(user_id)  # Извлечение API-ключа из базы данных
    if not api_key:
        return jsonify({"error": True, "message": "API-ключ не найден для данного user_id"}), 400

    # Проверяем доступ пользователя
    if not check_access(user_id):
        return jsonify({"error": True, "message": "У пользователя нет доступа"}), 403

    response_text = request.json.get("response")
    if not response_text:
        return jsonify({"error": True, "message": "Response is required"}), 400

    result = reply_to_review(api_key, review_id, response_text)

    if result:
        return jsonify({"message": "Reply sent successfully"})
    else:
        return jsonify({"error": True, "message": "Error sending reply"}), 500

def reply_to_review(api_key, review_id, reply_text):#Отправляет ответ на отзыв с использованием API WB и возвращает результат.
    url = "https://feedbacks-api.wildberries.ru/api/v1/feedbacks"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "accept": "*/*"
    }
    data = {
        "id": review_id,
        "text": reply_text
    }

    response = requests.patch(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка при отправке ответа на отзыв: {response.status_code}, пожалуйста, свяжитесь с поддержкой: @ltroy_sw")
        return None


#БЛОК РАБОТЫ С ИИ
@app.route("/api/v1/generate_response", methods=["POST"])
def generate_response():#принимает запрос на ответ на отзыв от ИИ и вызывает generate_gpt3_response
    prompt = request.json.get("prompt")
    if not prompt:
        return jsonify({"error": True, "message": "Требуется указать текст для генерации ответа"}), 400

    response = generate_gpt3_response(prompt)
    return jsonify({"response": response})

def generate_gpt3_response(prompt):#генерирует ответ на отзыв от ИИ
    content = f"Ответь на отзыв клиента: {prompt}"

    messages = [
        {"role": "user", "content": content}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=messages,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    return response.choices[0].message['content'].strip()

#ОСТАЛЬНОЕ
def main():#проверяет таблицу и запускает сервер
    create_table_if_not_exists()
    give_access(1572302344)
    app.run(host="localhost", port=12345, threaded=True)

if __name__ == "__main__":#запускает сервер
    main()
