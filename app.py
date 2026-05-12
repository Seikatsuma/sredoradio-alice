from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Пробуем "чистый" MP3 адрес (добавили /stream.mp3)
STREAM_URL = "https://listen10.myradio24.com/5559/stream.mp3"

def make_response(text, stream_url=None):
    response = {
        "text": text,
        "tts": text,
        "end_session": False
    }
    
    if stream_url:
        response["directives"] = {
            "audio_player": {
                "action": "Play",
                "item": {
                    "stream": {
                        "url": stream_url,
                        "offset_ms": 0,
                        "token": "sredo_v5_final"
                    },
                    "metadata": {
                        "title": "Радио Среда",
                        "sub_title": "Прямой эфир"
                    }
                }
            }
        }
        # Для колонок ОБЯЗАТЕЛЬНО закрываем сессию при старте плеера
        response["end_session"] = True
        
    return jsonify({
        "response": response,
        "version": "1.0"
    })

@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    request_obj = body.get("request", {})
    request_type = request_obj.get("type", "")
    command = request_obj.get("command", "").lower().strip()
    
    # Логируем ошибки плеера, если они придут от Яндекса
    if "AudioPlayer.PlaybackFailed" in request_type:
        app.logger.error(f"PLAYBACK FAILED: {request_obj.get('error', {})}")
        return jsonify({"version": "1.0", "response": {"end_session": True}})

    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    # Приветствие
    if body.get("session", {}).get("new", False) or not command:
        return make_response("Привет! Это Радио Среда. Чтобы включить эфир, скажите «включи».")

    # Включение
    if any(word in command for word in ["включи", "запусти", "да", "играй", "слушать", "старт"]):
        return make_response("Включаю!", stream_url=STREAM_URL)

    # Остановка
    if any(word in command for word in ["стоп", "выключи", "хватит", "останови"]):
        res = make_response("Выключаю.")
        res.json["response"]["directives"] = {"audio_player": {"action": "Stop"}}
        res.json["response"]["end_session"] = True
        return res

    return make_response("Скажите «включи», чтобы слушать радио.")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
