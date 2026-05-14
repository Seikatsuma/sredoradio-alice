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

# In-memory ring buffer (last 50 hits within the same serverless instance).
# NOTE: resets on every cold start — use ntfy.sh for cross-invocation monitoring.
_stream_log = collections.deque(maxlen=50)
_log_lock = threading.Lock()


def _ping_ntfy(ip, ua, range_hdr):
    """Fire-and-forget POST to ntfy.sh for persistent cross-invocation logging."""
    try:
        msg = f"ip={ip} ua={ua[:60]} range={range_hdr}"
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=msg.encode("utf-8"),
            headers={"Title": "Stream hit", "Priority": "low"},
            timeout=3,
        )
    except Exception:
        pass


def _log_stream_hit(req):
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ip": req.headers.get("X-Forwarded-For", req.remote_addr),
        "ua": req.headers.get("User-Agent", "-")[:120],
        "range": req.headers.get("Range", "-"),
    }
    with _log_lock:
        _stream_log.appendleft(entry)
    app.logger.info(
        f"STREAM_HIT ip={entry['ip']} ua={entry['ua'][:60]} range={entry['range']}"
    )
    threading.Thread(
        target=_ping_ntfy,
        args=(entry["ip"], entry["ua"], entry["range"]),
        daemon=True,
    ).start()


@app.route("/stream.mp3")
def stream_proxy():
    """
    Proxy for the live stream.
    Used as the AudioPlayer stream URL so every device connection is logged.
    Also used as <speaker audio> fallback for non-AudioPlayer surfaces.
    """
    _log_stream_hit(request)

    range_header = request.headers.get("Range")
    headers = {"Range": range_header} if range_header else {}

    def generate():
        with requests.get(
            RADIO_STREAM_URL, stream=True, timeout=30, headers=headers
        ) as r:
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


@app.route("/stream-log")
def stream_log():
    """Last hits to /stream.mp3 within this serverless instance."""
    with _log_lock:
        entries = list(_stream_log)
    return jsonify({"hits": len(entries), "log": entries})


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
        # AudioPlayer.Play directive — Yandex Station follows this.
        # We use the Vercel proxy URL so every Station connection is logged via ntfy.sh.
        response["directives"] = {
            "audio_player": {
                "action": "Play",
                "item": {
                    "stream": {
                        "url": proxy_url,
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
        response["end_session"] = True

        # <speaker audio> fallback for web/non-AudioPlayer surfaces.
        response["tts"] = f"<speaker audio='{proxy_url}'>"
        response["text"] = "Включаю Радио Среда."

    if stop:
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

    # ── AudioPlayer events ───────────────────────────────────────────────────
    if request_type == "AudioPlayer.PlaybackFinished":
        app.logger.info("PlaybackFinished — restarting stream")
        return make_response("Перезапускаю эфир.", play=True, has_audio_player=True)

    # NearlyFinished: queue the next play so Station connects seamlessly.
    if request_type == "AudioPlayer.PlaybackNearlyFinished":
        app.logger.info("PlaybackNearlyFinished — queuing next stream")
        return make_response("Продолжаю эфир.", play=True, has_audio_player=True)

    if request_type in (
        "AudioPlayer.PlaybackFailed",
        "AudioPlayer.PlaybackStopped",
    ):
        return jsonify({"version": "1.0", "response": {"end_session": False}})

    # ── New session ──────────────────────────────────────────────────────────
    if is_new_session:
        return make_response(
            "Привет! Это Радио Среда — прямой эфир. Скажите «включи», чтобы начать слушать.",
            has_audio_player=has_audio_player,
        )

    # ── Commands ─────────────────────────────────────────────────────────────
    PLAY_WORDS = [
        "включи", "запусти", "давай", "да", "играй", "слушать",
        "включить", "начни", "старт", "play",
    ]
    if any(w in command for w in PLAY_WORDS) or any(w in original for w in PLAY_WORDS):
        return make_response(
            "Включаю прямой эфир Радио Среда!",
            play=True,
            has_audio_player=has_audio_player,
        )

    STOP_WORDS = ["стоп", "выключи", "хватит", "останови", "тихо", "замолчи", "stop"]
    if any(w in command for w in STOP_WORDS) or any(w in original for w in STOP_WORDS):
        return make_response(
            "Выключаю.", stop=True, has_audio_player=has_audio_player
        )

    # Empty command → Alice is asking "Are you there?" → keep playing
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
    with _log_lock:
        hits = len(_stream_log)
        last = list(_stream_log)[:3]
    return jsonify({
        "status": "ok",
        "mode": "audioplayer_proxy + speaker_fallback + ntfy_monitor",
        "stream_direct": RADIO_STREAM_URL,
        "stream_proxy": f"{request.host_url}stream.mp3",
        "ntfy_monitor": f"https://ntfy.sh/{NTFY_TOPIC}",
        "stream_log_hits": hits,
        "last_hits": last,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
