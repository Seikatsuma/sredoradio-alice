from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Используем максимально совместимую ссылку
STREAM_URL = "https://myradio24.org/5559"

RADIO_NAME = "Радио Среда"

def make_response(text, play=False):
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
                        "token": "sredoradio_v1"
                    },
                    "metadata": {
                        "title": "Радио Среда",
                        "sub_title": "Сила Сообществ"
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
    
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if body.get("session", {}).get("new", False) or not command:
        return make_response("Привет! Это Радио Среда. Хотите послушать прямой эфир?")

    if any(word in command for word in ["включи", "запусти", "да", "давай", "играй", "слушать"]):
        return make_response("Запускаю прямой эфир!", play=True)

    if any(word in command for word in ["стоп", "выключи", "хватит", "хватит"]):
        resp = make_response("Выключаю Радио Среда. Хорошего дня!")
        resp.json["response"]["directives"] = {"audio_player": {"action": "Stop"}}
        resp.json["response"]["end_session"] = True
        return resp

    return make_response("Я вас не поняла. Скажите «включи», чтобы слушать радио.")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
