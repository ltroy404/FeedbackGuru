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


def get_api_key(user_id: int):
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

@app.route("/api/v1/add_api_key", methods=["POST"])
def receive_api_key():
    api_key = request.json.get("api_key")
    user_id = request.json.get("user_id")
    if not api_key or not user_id:
        return jsonify({"error": True, "message": "API-ключ и user_id обязательны для передачи"}), 400

    add_api_key(user_id, api_key)

    return jsonify({"message": "API-ключ успешно получен"})

def add_api_key(user_id: int, api_key: str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Проверка, есть ли уже такой пользователь
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()
    if data is None:
        c.execute("INSERT INTO users VALUES (?,?)", (user_id, api_key))
        print(f'API-ключ {api_key} добавлен в базу данных для пользователя {user_id}')
    else:
        c.execute("UPDATE users SET api_key=? WHERE user_id=?", (api_key, user_id))
        print(f'API-ключ {api_key} обновлен в базе данных для пользователя {user_id}')

    conn.commit()
    conn.close()
    print(get_api_key(user_id))

@app.route("/api/v1/remove_api_key", methods=["POST"])
def receive_user_id_for_removal():
    user_id = request.json.get("user_id")
    if not user_id:
        return jsonify({"error": True, "message": "User_id is required"}), 400

    remove_api_key(user_id)

    return jsonify({"message": "API key removed successfully"})

def remove_api_key(user_id: int):
    print(get_api_key(user_id))
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Удаление API ключа пользователя
    c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    print(get_api_key(user_id))


    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("SELECT api_key FROM users WHERE user_id=?", (user_id,))
    data = c.fetchone()

    conn.close()

    if data is not None:
        return data[0]  # Возвращаем api_key
    else:
        return None  # Если пользователь не найден в базе данных

@app.route("/api/v1/feedbacks/unanswered", methods=["GET"])
def get_unanswered_feedbacks():
    try:
        user_id = request.headers.get("user_id")
        if not user_id:
            return jsonify({"error": True, "message": "User_id не предоставлен"}), 400

        api_key = get_api_key(user_id)  # Извлечение API-ключа из базы данных
        if not api_key:
            return jsonify({"error": True, "message": "API-ключ не найден для данного user_id"}), 400

        take = request.args.get("take", 10)
        skip = request.args.get("skip", 0)
        headers = {"Authorization": api_key, "accept": "application/json"}
        params = {"take": take, "skip": skip, "answered": "false", "isAnswered": "false"}
        response = requests.get(f"{WB_API_URL}/api/v1/feedbacks", headers=headers, params=params)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            print(f"Error fetching data from Wildberries API. Status code: {response.status_code}, Response: {response.text}")

        return jsonify({"error": True, "message": "Error fetching data from Wildberries API"}), 500
    except Exception as e:
        print(f"Ошибка: {str(e)}, свяжитесь с поддержкой: @ltroy_sw")
        return jsonify({"error": True, "message": "Произошла ошибка, пожалуйста, свяжитесь с поддержкой: @ltroy_sw"}), 500

def reply_to_review(api_key, review_id, reply_text):
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

@app.route("/api/v1/generate_response", methods=["POST"])
def generate_response():
    prompt = request.json.get("prompt")
    if not prompt:
        return jsonify({"error": True, "message": "Требуется указать текст для генерации ответа"}), 400

    response = generate_gpt3_response(prompt)
    return jsonify({"response": response})

def generate_gpt3_response(prompt):
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

@app.route("/api/v1/feedbacks/<review_id>/reply", methods=["POST"])
def post_feedback_reply(review_id):
    user_id = request.headers.get("user_id")
    if not user_id:
        return jsonify({"error": True, "message": "User_id не предоставлен"}), 400

    api_key = get_api_key(user_id)  # Извлечение API-ключа из базы данных
    if not api_key:
        return jsonify({"error": True, "message": "API-ключ не найден для данного user_id"}), 400

    response_text = request.json.get("response")
    if not response_text:
        return jsonify({"error": True, "message": "Response is required"}), 400

    result = reply_to_review(api_key, review_id, response_text)

    if result:
        return jsonify({"message": "Reply sent successfully"})
    else:
        return jsonify({"error": True, "message": "Error sending reply"}), 500

def main():
    create_table_if_not_exists()
    app.run(host="localhost", port=12345, threaded=True)

if __name__ == "__main__":
    main()
