from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Исходный поток радио
RADIO_STREAM_URL = "https://listen10.myradio24.com/5559"

@app.route("/stream.mp3")
def stream_proxy():
    """
    Прокси-сервер для потока. 
    Добавляем заголовки, которые любит плеер Алисы (Range, Content-Type).
    """
    def generate():
        # Пересылаем поток чанками
        with requests.get(RADIO_STREAM_URL, stream=True, timeout=10) as r:
            for chunk in r.iter_content(chunk_size=8192):
                yield chunk

    return Response(
        stream_with_context(generate()),
        content_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

def make_response(text, play=False, stop=False):
    # Пытаемся отправить директиву В ЛЮБОМ СЛУЧАЕ, игнорируя проверку интерфейсов.
    # На реальных колонках это может сработать, даже если консоль говорит обратное.
    
    # Получаем актуальный хост для ссылки на прокси
    host = request.host_url.rstrip("/")
    proxy_url = f"{host}/stream.mp3"
    
    response = {
        "text": text,
        "tts": text,
        "end_session": False
    }
    
    if play:
        # Силовой запуск плеера
        response["directives"] = {
            "audio_player": {
                "action": "Play",
                "item": {
                    "stream": {
                        "url": proxy_url,
                        "offset_ms": 0,
                        "token": "sredo_force_v1"
                    },
                    "metadata": {
                        "title": "Радио Среда",
                        "sub_title": "Сила Сообществ"
                    }
                }
            }
        }
        # Для плеера сессия ОБЯЗАТЕЛЬНО должна быть закрыта (True)
        response["end_session"] = True

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
    request_obj = body.get("request", {})
    request_type = request_obj.get("type", "")
    command = request_obj.get("command", "").lower().strip()
    is_new_session = body.get("session", {}).get("new", False)

    # Логируем всё для отладки
    app.logger.info(f"REQ: {request_type} | CMD: {command} | NEW: {is_new_session}")

    # Обработка событий плеера (обязательно для стабильности)
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if is_new_session or not command:
        return make_response("Привет! Это Радио Среда. Я настроила прямой эфир. Сказать «включи»?")

    if any(word in command for word in ["включи", "запусти", "да", "давай", "играй", "слушать"]):
        # Мы не проверяем наличие плеера в meta.interfaces, а просто шлем команду.
        # Если устройство физически может играть — оно заиграет.
        return make_response("Включаю прямой эфир Радио Среда!", play=True)

    if any(word in command for word in ["стоп", "выключи", "хватит", "останови"]):
        return make_response("Выключаю радио. До встречи!", stop=True)

    return make_response("Я вас не поняла. Просто скажите «включи», чтобы слушать радио.")

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "active",
        "mode": "force_player",
        "stream_url": f"{request.host_url}stream.mp3"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
