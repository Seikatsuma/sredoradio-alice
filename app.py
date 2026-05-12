from flask import Flask, request, jsonify
import logging
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Прямая ссылка на поток (проверено: работает в MP3)
STREAM_URL = "https://listen10.myradio24.com/5559"

RADIO_NAME = "Радио Среда"
RADIO_SUBTITLE = "Сила Сообществ"

HELP_TEXT = (
    "Это навык Радио Среда. "
    "Скажите «включи» или «запусти» — и я начну трансляцию. "
    "Скажите «стоп» или «выключи» — и я остановлюсь. "
    "Чем могу помочь?"
)

WELCOME_TEXT = f"Привет! Это {RADIO_NAME} — радио о силе сообществ. Хотите послушать прямой эфир?"
STOP_TEXT = f"Выключаю {RADIO_NAME}. Буду ждать вас снова! Хорошего дня!"
UNKNOWN_TEXT = "Я вас не совсем поняла. Просто скажите «включи», чтобы слушать радио, или «помощь», если нужны подробности."


def make_response(text, tts=None, play=False, stop=False, end_session=False, token=None):
    resp = {
        "version": "1.0",
        "response": {
            "text": text,
            "tts": tts or text,
            "end_session": end_session
        }
    }
    
    if play:
        # Используем уникальный токен для каждого запуска, чтобы избежать кеширования Алисой
        play_token = token or f"token_{int(time.time())}"
        resp["response"]["directives"] = {
            "audio_player": {
                "action": "Play",
                "item": {
                    "stream": {
                        "url": STREAM_URL,
                        "offset_ms": 0,
                        "token": play_token
                    },
                    "metadata": {
                        "title": RADIO_NAME,
                        "sub_title": RADIO_SUBTITLE
                        # Убрали art, так как ссылка на обложку была битой и могла блокировать плеер
                    }
                }
            }
        }
    elif stop:
        resp["response"]["directives"] = {
            "audio_player": {"action": "Stop"}
        }
        
    return jsonify(resp)


def is_intent(command, keywords):
    return any(word in command for word in keywords)


@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json
    if not body:
        return jsonify({"version": "1.0", "response": {"text": "Ошибка: пустой запрос", "end_session": True}}), 400

    request_type = body.get("request", {}).get("type", "")
    command = body.get("request", {}).get("command", "").lower().strip()
    is_new_session = body.get("session", {}).get("new", False)
    session_id = body.get("session", {}).get("session_id", "default")

    app.logger.info(f"Request: type={request_type} | command='{command}' | new={is_new_session}")

    # Обработка событий аудио-плеера
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if is_new_session:
        return make_response(WELCOME_TEXT, play=False)

    if not command and not is_new_session:
         return make_response(WELCOME_TEXT, play=False)

    if is_intent(command, ["включи", "запусти", "начни", "старт", "включить",
                           "запустить", "включай", "играй", "слушать", "слушай", "да", "хочу", "давай"]):
        return make_response(f"Запускаю {RADIO_NAME}!", play=True, token=session_id)

    if is_intent(command, ["стоп", "выключи", "останови", "хватит", "тихо",
                           "замолчи", "выключить", "остановить", "пауза", "нет", "не надо"]):
        return make_response(STOP_TEXT, stop=True, end_session=True)

    if is_intent(command, ["помощь", "помоги", "что умеешь", "что ты умеешь",
                           "команды", "инструкция"]):
        return make_response(HELP_TEXT)

    return make_response(UNKNOWN_TEXT)


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "skill": RADIO_NAME})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
