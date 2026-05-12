from flask import Flask, request, jsonify, Response
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Прямой поток Средорадио
SREDO_STREAM_URL = "https://listen10.myradio24.com/5559"

@app.route("/stream.mp3")
def stream_proxy():
    """Прокси-сервер, который забирает поток и отдает его Алисе как чистый файл"""
    def generate():
        try:
            # Запрашиваем поток с внешнего сервера
            with requests.get(SREDO_STREAM_URL, stream=True, timeout=10) as r:
                r.raise_for_status()
                # Передаем чанки данных Алисе в реальном времени
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
        except Exception as e:
            app.logger.error(f"Proxy error: {e}")
    
    return Response(generate(), mimetype="audio/mpeg")

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
                        "token": "sredo_proxy_v1"
                    },
                    "metadata": {
                        "title": "Радио Среда",
                        "sub_title": "Прямой эфир"
                    }
                }
            }
        }
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
    
    if "AudioPlayer." in request_type:
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if body.get("session", {}).get("new", False) or not command:
        return make_response("Привет! Это Радио Среда. Хотите послушать прямой эфир?")

    if any(word in command for word in ["включи", "запусти", "да", "играй", "слушать", "старт"]):
        # Теперь мы даем Алисе ссылку НА НАШ СОБСТВЕННЫЙ СЕРВЕР
        # Vercel автоматически подставит домен в заголовки
        host = request.headers.get("Host", "sredoradio-alice.vercel.app")
        my_stream_url = f"https://{host}/stream.mp3"
        return make_response("Включаю!", stream_url=my_stream_url)

    if any(word in command for word in ["стоп", "выключи", "хватит"]):
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
