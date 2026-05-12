from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

STREAM_URL = "https://listen10.myradio24.com/5559"

def make_response(text, play=False):
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
                        "url": STREAM_URL,
                        "offset_ms": 0,
                        "token": "sredo_final_v1"
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
        return make_response("Привет! Это Радио Среда — радио о силе сообществ. Хотите послушать прямой эфир?")

    if any(word in command for word in ["включи", "запусти", "да", "давай", "играй", "слушать"]):
        return make_response("Включаю прямой эфир!", play=True)

    if any(word in command for word in ["стоп", "выключи", "хватит"]):
        res = make_response("Выключаю Радио Среда. Хорошего дня!")
        res.json["response"]["directives"] = {"audio_player": {"action": "Stop"}}
        res.json["response"]["end_session"] = True
        return res

    return make_response("Я вас не совсем поняла. Просто скажите «включи», чтобы слушать радио.")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
