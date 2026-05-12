from flask import Flask, request, jsonify
import logging
import time
import random

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Самый прямой адрес потока
STREAM_URL = "https://listen10.myradio24.com/5559"

def make_response(text, play=False):
    # Генерируем абсолютно новый токен для каждой попытки
    random_token = f"token_{int(time.time())}_{random.randint(1000, 9999)}"
    
    resp = {
        "version": "1.0",
        "response": {
            "text": text,
            "tts": text,
            "end_session": False
        }
    }
    
    if play:
        resp["response"]["directives"] = {
            "audio_player": {
                "action": "Play",
                "item": {
                    "stream": {
                        "url": STREAM_URL,
                        "offset_ms": 0,
                        "token": random_token
                    },
                    "metadata": {
                        "title": "Радио Среда",
                        "sub_title": "Прямой эфир"
                    }
                }
            }
        }
    return jsonify(resp)

@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    request_type = body.get("request", {}).get("type", "")
    command = body.get("request", {}).get("command", "").lower().strip()
    
    # Технические ответы для Алисы
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    # Приветствие
    if body.get("session", {}).get("new", False) or not command:
        return make_response("Привет! Это Радио Среда. Хотите послушать прямой эфир?")

    # Команды на включение
    if any(word in command for word in ["включи", "запусти", "да", "давай", "играй", "слушать", "старт"]):
        return make_response("Включаю Среду!", play=True)

    # Команды на остановку
    if any(word in command for word in ["стоп", "выключи", "останови", "хватит"]):
        res = make_response("Выключаю радио. Хорошего дня!")
        res.json["response"]["directives"] = {"audio_player": {"action": "Stop"}}
        res.json["response"]["end_session"] = True
        return res

    return make_response("Я вас не поняла. Просто скажите «включи», чтобы слушать радио.")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
