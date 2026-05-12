from flask import Flask, request, jsonify
import logging
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ТЕСТОВАЯ ССЫЛКА (Наше Радио), которая точно работает в Алисе
STREAM_URL = "https://nashe1.hostingradio.ru/nashe-128.mp3"

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
                        "token": f"test_{int(time.time())}"
                    },
                    "metadata": {
                        "title": "Тест звука",
                        "sub_title": "Проверка плеера"
                    }
                }
            }
        }
    return jsonify(resp)

@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    command = body.get("request", {}).get("command", "").lower().strip()
    if body.get("session", {}).get("new", False) or not command:
        return make_response("Привет! Это проверка звука. Скажите «включи», чтобы проверить плеер.")
    if any(word in command for word in ["включи", "запусти", "да"]):
        return make_response("Запускаю тестовый поток!", play=True)
    return make_response("Скажите «включи».")

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
