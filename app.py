from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    meta = body.get("meta", {})
    interfaces = meta.get("interfaces", {})
    
    has_player = "audio_player" in interfaces
    
    if body.get("session", {}).get("new", False):
        if has_player:
            return jsonify({
                "version": "1.0",
                "response": {
                    "text": "Вижу плеер, включаю! Хотите послушать?",
                    "tts": "Вижу плеер, включаю! Хотите послушать?",
                    "end_session": False
                }
            })
        else:
            return jsonify({
                "version": "1.0",
                "response": {
                    "text": "Плеера не вижу, только текст. Попробуйте на колонке.",
                    "tts": "Плеера не вижу, только текст. Попробуйте на колонке.",
                    "end_session": True
                }
            })

    # На команду "да" пробуем включить
    return jsonify({
        "version": "1.0",
        "response": {
            "text": "Пробую запустить поток...",
            "directives": {
                "audio_player": {
                    "action": "Play",
                    "item": {
                        "stream": {
                            "url": "https://listen10.myradio24.com/5559",
                            "offset_ms": 0,
                            "token": "debug_1"
                        }
                    }
                }
            },
            "end_session": True
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
