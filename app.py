from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import logging
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

RADIO_STREAM_URL = "https://listen10.myradio24.com/5559"


@app.route("/stream.mp3")
def stream_proxy():
    """
    Прокси-сервер для потока.
    Используется для <speaker audio='URL'> в TTS — добавляет заголовки Accept-Ranges
    и Content-Type: audio/mpeg, которые требует Яндекс.
    """
    range_header = request.headers.get("Range", None)
    headers = {"Range": range_header} if range_header else {}

    def generate():
        with requests.get(RADIO_STREAM_URL, stream=True, timeout=30, headers=headers) as r:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

    return Response(
        stream_with_context(generate()),
        content_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def make_response(text, play=False, stop=False, has_audio_player=False):
    host = request.host_url.rstrip("/")
    proxy_url = f"{host}/stream.mp3"
    token = f"sredo_{int(time.time())}"

    response = {
        "text": text,
        "tts": text,
        "end_session": False,
    }

    if play:
        if has_audio_player:
            # Устройство поддерживает AudioPlayer — используем прямой URL потока
            # (НЕ прокси, чтобы избежать serverless timeout Vercel)
            response["directives"] = {
                "audio_player": {
                    "action": "Play",
                    "item": {
                        "stream": {
                            "url": RADIO_STREAM_URL,
                            "offset_ms": 0,
                            "token": token,
                        },
                        "metadata": {
                            "title": "Радио Среда",
                            "sub_title": "Прямой эфир",
                        },
                    },
                }
            }
            response["end_session"] = True  # AudioPlayer требует закрытой сессии
        else:
            # Вариант Б: <speaker audio> — TTS-инъекция аудио.
            # Яндекс забирает поток с нашего прокси и воспроизводит его.
            # Для живого стрима Яндекс может играть непрерывно (поведение не задокументировано).
            # end_session=False позволяет перезапустить, когда Алиса спросит "Вы здесь?"
            response["tts"] = f"<speaker audio='{proxy_url}'>"
            response["text"] = "Радио Среда — прямой эфир."
            response["end_session"] = False

    if stop:
        if has_audio_player:
            response["directives"] = {"audio_player": {"action": "Stop"}}
        response["text"] = "Выключаю радио. До встречи!"
        response["tts"] = "Выключаю радио. До встречи!"
        response["end_session"] = True

    return jsonify({"version": "1.0", "response": response})


@app.route("/webhook", methods=["POST"])
@app.route("/", methods=["POST"])
def webhook():
    body = request.json or {}
    request_obj = body.get("request", {})
    request_type = request_obj.get("type", "")
    command = request_obj.get("command", "").lower().strip()
    original = request_obj.get("original_utterance", "").lower().strip()
    is_new_session = body.get("session", {}).get("new", False)
    interfaces = body.get("meta", {}).get("interfaces", {})
    has_audio_player = "audio_player" in interfaces

    app.logger.info(
        f"TYPE={request_type} | CMD={command!r} | NEW={is_new_session} | AP={has_audio_player}"
    )

    # События плеера — при PlaybackFinished перезапускаем поток
    if request_type == "AudioPlayer.PlaybackFinished":
        app.logger.info("Stream ended — restarting")
        return make_response("Перезапускаю эфир.", play=True, has_audio_player=True)

    if request_type in (
        "AudioPlayer.PlaybackNearlyFinished",
        "AudioPlayer.PlaybackFailed",
        "AudioPlayer.PlaybackStopped",
    ):
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    # Новая сессия
    if is_new_session:
        return make_response(
            "Привет! Это Радио Среда — прямой эфир. Скажите «включи», чтобы начать слушать.",
            has_audio_player=has_audio_player,
        )

    # Команда включить
    PLAY_WORDS = ["включи", "запусти", "давай", "да", "играй", "слушать", "включить", "начни", "старт"]
    if any(w in command for w in PLAY_WORDS) or any(w in original for w in PLAY_WORDS):
        return make_response(
            "Включаю прямой эфир Радио Среда!",
            play=True,
            has_audio_player=has_audio_player,
        )

    # Команда выключить
    STOP_WORDS = ["стоп", "выключи", "хватит", "останови", "тихо", "замолчи"]
    if any(w in command for w in STOP_WORDS) or any(w in original for w in STOP_WORDS):
        return make_response(
            "Выключаю.", stop=True, has_audio_player=has_audio_player
        )

    # Пустая команда = Алиса спросила "Вы здесь?" после окончания аудио → перезапускаем
    if not command:
        return make_response(
            "Продолжаю эфир.",
            play=True,
            has_audio_player=has_audio_player,
        )

    return make_response(
        "Скажите «включи», чтобы слушать Радио Среда.",
        has_audio_player=has_audio_player,
    )


@app.route("/", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "mode": "tts_speaker_injection",
            "stream_direct": RADIO_STREAM_URL,
            "stream_proxy": f"{request.host_url}stream.mp3",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
