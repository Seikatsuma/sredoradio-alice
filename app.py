from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Прямая ссылка на поток с добавлением .mp3 для лучшей совместимости
STREAM_URL = "https://listen10.myradio24.com/5559/stream.mp3"

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
                            "token": "sredo_v2_direct"
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
            response["text"] += " К сожалению, ваше устройство не поддерживает воспроизведение аудио через плеер."
            response["tts"] += " К сожалению, ваше устройство не поддерживает воспроизведение аудио через плеер."

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
    has_player = "audio_player" in interfaces
    
    request_obj = body.get("request", {})
    request_type = request_obj.get("type", "")
    command = request_obj.get("command", "").lower().strip()
    is_new_session = body.get("session", {}).get("new", False)

    # Логируем наличие плеера
    app.logger.info(f"Interfaces: {interfaces.keys()}")

    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if is_new_session or not command:
        welcome = f"Привет! Это {RADIO_NAME}. "
        if has_player:
            welcome += "Я могу включить прямой эфир. Сказать «включи»?"
        else:
            welcome += "К сожалению, я вижу, что ваше устройство не поддерживает аудио-плеер, поэтому я не смогу запустить радио здесь."
        return make_response(welcome, has_player=has_player)

    if any(word in command for word in ["включи", "запусти", "да", "давай", "играй", "слушать"]):
        return make_response("Включаю прямой эфир!", play=True, has_player=has_player)

    if any(word in command for word in ["стоп", "выключи", "хватит", "останови"]):
        return make_response("Выключаю Радио Среда. Хорошего дня!", stop=True)

    if any(word in command for word in ["помощь", "что ты умеешь"]):
        help_text = "Я умею транслировать Радио Среда. Просто скажите «включи», и я запущу поток."
        return make_response(help_text, has_player=has_player)

    return make_response("Я вас не совсем поняла. Просто скажите «включи», чтобы слушать радио.", has_player=has_player)

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "player_url": STREAM_URL})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
