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

    # Если это технический запрос от плеера - отвечаем пустотой
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    # Проверяем, поддерживает ли устройство плеер
    has_player = "audio_player" in interfaces

    # Приветствие
    if body.get("session", {}).get("new", False) or not command:
        if not has_player:
            return jsonify({
                "version": "1.0",
                "response": {
                    "text": "Привет! Это Радио Среда. К сожалению, ваше устройство не поддерживает аудио-плеер. Попробуйте запустить меня на Яндекс Станции.",
                    "end_session": True
                }
            })
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
                "text": "Включаю!",
                "tts": "Включаю!",
                "directives": {
                    "audio_player": {
                        "action": "Play",
                        "item": {
                            "stream": {
                                "url": STREAM_URL,
                                "offset_ms": 0,
                                "token": "1"
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
                "text": "Выключаю Радио Среда.",
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
