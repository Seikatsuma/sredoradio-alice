from flask import Flask, request, jsonify, Response
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Исходный поток
RADIO_STREAM_URL = "https://listen10.myradio24.com/5559"

@app.route("/stream.mp3")
def stream_proxy():
    def generate():
        # Проксируем поток через наш сервер для максимальной совместимости
        with requests.get(RADIO_STREAM_URL, stream=True) as r:
            for chunk in r.iter_content(chunk_size=4096):
                yield chunk
    return Response(generate(), mimetype="audio/mpeg")

def make_response(text, play=False):
    # Теперь ссылка ведет на наш собственный сервер
    # Vercel автоматически подставит домен
    host = request.host_url.rstrip("/")
    proxy_url = f"{host}/stream.mp3"
    
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
                        "url": proxy_url,
                        "offset_ms": 0,
                        "token": "sredo_proxy_v1"
                    },
                    "metadata": {
                        "title": "Радио Среда",
                        "sub_title": "Прямой эфир"
                    }
                }
            }
        }
        resp["response"]["end_session"] = True
    return jsonify(resp)

@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    request_obj = body.get("request", {})
    request_type = request_obj.get("type", "")
    command = request_obj.get("command", "").lower().strip()

    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if body.get("session", {}).get("new", False) or not command:
        return make_response("Привет! Это Радио Среда. Хотите послушать прямой эфир?")

    if any(word in command for word in ["включи", "запусти", "да", "давай", "играй", "слушать"]):
        return make_response("Включаю прямой эфир!", play=True)

    if any(word in command for word in ["стоп", "выключи", "хватит"]):
        res = make_response("Выключаю Радио Среда. Хорошего дня!")
        res.json["response"]["directives"] = {"audio_player": {"action": "Stop"}}
        res.json["response"]["end_session"] = True
        return res

    return make_response("Я вас не поняла. Просто скажите «включи», чтобы слушать радио.")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "proxy": "active"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
