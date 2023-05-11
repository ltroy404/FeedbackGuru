import socket
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

WB_API_URL = "https://feedbacks-api.wildberries.ru"
openai.api_key = "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"

@app.route("/api/v1/feedbacks/unanswered", methods=["GET"])
def get_unanswered_feedbacks():
    try:
        api_key = request.headers.get("Authorization")
        if not api_key:
            return jsonify({"error": True, "message": "API-ключ не предоставлен"}), 400

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
    api_key = request.headers.get("Authorization")
    if not api_key:
        return jsonify({"error": True, "message": "API-ключ не предоставлен"}), 400

    response_text = request.json.get("response")
    if not response_text:
        return jsonify({"error": True, "message": "Response is required"}), 400

    result = reply_to_review(api_key, review_id, response_text)

    if result:
        return jsonify({"message": "Reply sent successfully"})
    else:
        return jsonify({"error": True, "message": "Error sending reply to review"}), 500



def main():
    app.run(host="localhost", port=12345, threaded=True)

if __name__ == "__main__":
    main()
