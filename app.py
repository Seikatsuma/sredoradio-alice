from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Прямая ссылка на Наше Радио (для 100% теста)
TEST_STREAM = "https://nashe1.hostingradio.ru/nashe-128.mp3"
# Прямая ссылка на Средорадио
SREDO_STREAM = "https://listen10.myradio24.com/5559"

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
                        "token": "sredoradio_token_final"
                    },
                    "metadata": {
                        "title": "Радио Среда"
                    }
                }
            }
        }
        # ВАЖНО: Для запуска плеера на многих устройствах сессию нужно закрыть
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
    
    # Обработка технических событий (обязательно для AudioPlayer)
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    # Приветствие (новая сессия)
    if body.get("session", {}).get("new", False) or not command:
        return make_response("Привет! Это Радио Среда. Чтобы включить эфир, скажите «запусти» или «включи».")

    # Команды на запуск
    if any(word in command for word in ["включи", "запусти", "да", "играй", "слушать"]):
        # ВОЗВРАЩАЕМ СРЕДОРАДИО (я уверен в ссылке)
        return make_response("Включаю прямой эфир Радио Среда!", stream_url=SREDO_STREAM)

    # Команды на остановку
    if any(word in command for word in ["стоп", "выключи", "хватит"]):
        res = make_response("Выключаю. Хорошего дня!")
        res.json["response"]["directives"] = {"audio_player": {"action": "Stop"}}
        res.json["response"]["end_session"] = True
        return res

    return make_response("Я вас не поняла. Просто скажите «включи», чтобы слушать радио.")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
