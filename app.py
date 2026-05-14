from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import logging
import time
import threading
import collections

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

RADIO_STREAM_URL = "https://listen10.myradio24.com/5559"
NTFY_TOPIC = "sredoradio-alice-stream"

_stream_log = collections.deque(maxlen=50)
_log_lock = threading.Lock()


def _ping_ntfy(ip, ua, source):
    try:
        msg = f"ip={ip} ua={ua[:60]} src={source}"
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=msg.encode("utf-8"),
            headers={"Title": "Stream hit", "Priority": "low"},
            timeout=3,
        )
    except Exception:
        pass


def _log_hit(req, source="proxy"):
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": req.headers.get("X-Forwarded-For", req.remote_addr),
        "ua": req.headers.get("User-Agent", "-")[:120],
        "range": req.headers.get("Range", "-"),
        "source": source,
    }
    with _log_lock:
        _stream_log.appendleft(entry)
    app.logger.info(f"HIT src={source} ip={entry['ip']} ua={entry['ua'][:60]}")
    threading.Thread(
        target=_ping_ntfy,
        args=(entry["ip"], entry["ua"], source),
        daemon=True,
    ).start()


@app.route("/stream.mp3")
def stream_proxy():
    """
    Infinite live-stream proxy with ICY headers.
    Used as <speaker audio> URL — no Content-Length so Alice treats it as live.
    Also serves AudioPlayer if Yandex ever unblocks it for this skill.
    """
    _log_hit(request, source="proxy")

    def generate():
        with requests.get(
            RADIO_STREAM_URL,
            stream=True,
            timeout=None,
            headers={
                "Icy-MetaData": "1",
                "User-Agent": "Mozilla/5.0 AliceRadioProxy/1.0",
            },
        ) as r:
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

    return Response(
        stream_with_context(generate()),
        status=200,
        content_type="audio/mpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
            "X-Accel-Buffering": "no",
            "icy-name": "Радио Среда",
            "icy-genre": "Talk",
            "icy-pub": "1",
            "icy-br": "128",
        },
    )


@app.route("/stream-log")
def stream_log():
    with _log_lock:
        entries = list(_stream_log)
    return jsonify({"hits": len(entries), "log": entries})


def make_response(text, play=False, stop=False):
    host = request.host_url.rstrip("/")
    proxy_url = f"{host}/stream.mp3"

    response = {
        "text": text,
        "tts": text,
        "end_session": False,
    }

    if play:
        # Variant B: <speaker audio> with infinite live stream.
        # Use direct stream URL to avoid Vercel function timeout (10s on free tier).
        # The proxy URL is kept for AudioPlayer future use + manual testing.
        response["text"] = "Включаю Радио Среда."
        response["tts"] = f"<speaker audio='{RADIO_STREAM_URL}'>"
        response["end_session"] = True

    if stop:
        response["text"] = "Выключаю. До встречи!"
        response["tts"] = "Выключаю. До встречи!"
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

    app.logger.info(f"TYPE={request_type} | CMD={command!r} | NEW={is_new_session}")

    # AudioPlayer events (kept for forward compatibility)
    if request_type == "AudioPlayer.PlaybackFinished":
        return make_response("Перезапускаю эфир.", play=True)

    if request_type == "AudioPlayer.PlaybackNearlyFinished":
        return make_response("Продолжаю эфир.", play=True)

    if request_type in ("AudioPlayer.PlaybackFailed", "AudioPlayer.PlaybackStopped"):
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    if is_new_session:
        return make_response(
            "Привет! Это Радио Среда — прямой эфир. Скажите «включи», чтобы начать слушать."
        )

    PLAY_WORDS = [
        "включи", "запусти", "давай", "да", "играй", "слушать",
        "включить", "начни", "старт", "play",
    ]
    if any(w in command for w in PLAY_WORDS) or any(w in original for w in PLAY_WORDS):
        _log_hit(request, source="skill_play")
        return make_response("Включаю прямой эфир Радио Среда!", play=True)

    STOP_WORDS = ["стоп", "выключи", "хватит", "останови", "тихо", "замолчи", "stop"]
    if any(w in command for w in STOP_WORDS) or any(w in original for w in STOP_WORDS):
        return make_response("Выключаю.", stop=True)

    if not command:
        return make_response("Продолжаю эфир.", play=True)

    return make_response("Скажите «включи», чтобы слушать Радио Среда.")


@app.route("/", methods=["GET"])
def health():
    with _log_lock:
        hits = len(_stream_log)
        last = list(_stream_log)[:3]
    return jsonify({
        "status": "ok",
        "mode": "speaker_audio_infinite_stream",
        "stream_proxy": f"{request.host_url}stream.mp3",
        "stream_direct": RADIO_STREAM_URL,
        "ntfy_monitor": f"https://ntfy.sh/{NTFY_TOPIC}",
        "stream_log_hits": hits,
        "last_hits": last,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
