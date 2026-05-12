from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

STREAM_URL = "https://listen10.myradio24.com/5559"

@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    meta = body.get("meta", {})
    interfaces = meta.get("interfaces", {})
    request_obj = body.get("request", {})
    request_type = request_obj.get("type", "")
    command = request_obj.get("command", "").lower().strip()

    # Логируем интерфейсы для отладки
    app.logger.info(f"Interfaces: {list(interfaces.keys())}")
    app.logger.info(f"Request Type: {request_type} | Command: {command}")

    # Технические запросы от плеера
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    # Приветствие
    if body.get("session", {}).get("new", False) or not command:
        return jsonify({
            "version": "1.0",
            "response": {
                "text": "Привет! Это Радио Среда. Хотите послушать прямой эфир?",
                "tts": "Привет! Это Радио Среда. Хотите послушать прямой эфир?",
                "end_session": False
            }
        })

    # Команда на включение
    if any(word in command for word in ["включи", "запусти", "да", "играй", "слушать"]):
        return jsonify({
            "version": "1.0",
            "response": {
                "text": "Включаю прямой эфир!",
                "tts": "Включаю прямой эфир!",
                "directives": {
                    "audio_player": {
                        "action": "Play",
                        "item": {
                            "stream": {
                                "url": STREAM_URL,
                                "offset_ms": 0,
                                "token": "sredo_v1"
                            },
                            "metadata": {
                                "title": "Радио Среда",
                                "sub_title": "Сила Сообществ"
                            }
                        }
                    }
                },
                "end_session": True
            }
        })

    # Остановка
    if any(word in command for word in ["стоп", "выключи", "хватит"]):
        return jsonify({
            "version": "1.0",
            "response": {
                "text": "Выключаю Радио Среда. Хорошего дня!",
                "directives": {
                    "audio_player": {"action": "Stop"}
                },
                "end_session": True
            }
        })

    return jsonify({
        "version": "1.0",
        "response": {
            "text": "Я вас не поняла. Скажите «включи», чтобы слушать радио.",
            "end_session": False
        }
    })

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
