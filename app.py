from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Рабочая ссылка на поток
STREAM_URL = "https://listen10.myradio24.com/5559"

RADIO_NAME = "Радио Среда"
RADIO_SUBTITLE = "Сила Сообществ"

def make_response(text, play=False, stop=False, has_player=True):
    response = {
        "text": text,
        "tts": text,
        "end_session": False
    }
    
    if play:
        if has_player:
            response["directives"] = {
                "audio_player": {
                    "action": "Play",
                    "item": {
                        "stream": {
                            "url": STREAM_URL,
                            "offset_ms": 0,
                            "token": "sredo_v3_direct"
                        },
                        "metadata": {
                            "title": RADIO_NAME,
                            "sub_title": RADIO_SUBTITLE
                        }
                    }
                }
            }
            response["end_session"] = True
        else:
            # Если плеер не поддерживается устройством
            msg = " К сожалению, это устройство не поддерживает аудио-плеер. Попробуйте запустить этот навык на Яндекс Станции или в мобильном приложении Яндекс с Алисой."
            response["text"] += msg
            response["tts"] += msg

    if stop:
        response["directives"] = {
            "audio_player": {
                "action": "Stop"
            }
        }
        response["end_session"] = True

    return jsonify({
        "version": "1.0",
        "response": response
    })

@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    meta = body.get("meta", {})
    interfaces = meta.get("interfaces", {})
    
    # Проверяем наличие интерфейса аудио-плеера
    has_player = "audio_player" in interfaces
    
    request_obj = body.get("request", {})
    request_type = request_obj.get("type", "")
    command = request_obj.get("command", "").lower().strip()
    is_new_session = body.get("session", {}).get("new", False)

    app.logger.info(f"Request: {request_type} | Has Player: {has_player} | Interfaces: {list(interfaces.keys())}")

    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if is_new_session or not command:
        welcome = f"Привет! Это {RADIO_NAME}. "
        if has_player:
            welcome += "Я могу включить прямой эфир. Сказать «включи»?"
        else:
            welcome += "Я вижу, что ваше устройство не поддерживает плеер. Чтобы слушать радио, запустите меня на колонке или в приложении Яндекс."
        return make_response(welcome, has_player=has_player)

    if any(word in command for word in ["включи", "запусти", "да", "давай", "играй", "слушать"]):
        return make_response("Включаю прямой эфир!", play=True, has_player=has_player)

    if any(word in command for word in ["стоп", "выключи", "хватит", "останови"]):
        return make_response("Выключаю Радио Среда. Хорошего дня!", stop=True)

    return make_response("Я вас не совсем поняла. Просто скажите «включи», чтобы слушать радио.", has_player=has_player)

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "stream": STREAM_URL})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
