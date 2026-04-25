import sys
import os
import json
import threading
import numpy as np
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from fastrtc import Stream, ReplyOnPause, get_stt_model, get_tts_model
from loguru import logger

load_dotenv()

# ─────────────────────────────────────────────
# Client & Models
# ─────────────────────────────────────────────
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")

logger.info("Loading STT model…")
stt_model = get_stt_model()

logger.info("Loading TTS model…")
tts_model = get_tts_model()

logger.info("Models ready.")

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
ENERGY_THRESHOLD = 400
SYSTEM_PROMPT = (
    "You are a professional, calm, and eloquent AI voice assistant. "
    "Respond clearly, concisely, and naturally. "
    "Keep answers brief (1–3 sentences for conversational queries). "
    "Do not use emojis, markdown, or special characters."
)


# ─────────────────────────────────────────────
# Per-Connection Handler
# ─────────────────────────────────────────────
class PerConnectionHandler(ReplyOnPause):
    """
    Subclass of ReplyOnPause that creates a fresh, fully-isolated handler
    for each WebRTC connection via copy().

    The echo closure captures `self`, so each connection has its own:
      - interrupt_event (threading.Event)
      - send_message_sync calls to the data channel
    """

    def __init__(self):
        interrupt_event = threading.Event()
        handler_ref = self   # forward reference captured by closures below

        # ── Startup greeting ──────────────────────────────────────
        def startup():
            text = "Hello, how can I help you today?"
            logger.info("[startup] Greeting user…")
            for chunk in tts_model.stream_tts_sync(text):
                yield chunk

        # ── Core voice handler ────────────────────────────────────
        def echo(audio):
            try:
                if audio is None:
                    return

                sample_rate, audio_array = (
                    audio if isinstance(audio, tuple) else (16000, audio)
                )

                if audio_array is None or len(audio_array) == 0:
                    return

                audio_np = np.asarray(audio_array, dtype=np.int16)
                rms = float(np.sqrt(np.mean(audio_np.astype(np.float32) ** 2)))

                # ── Interruption detection ─────────────────────────
                if rms >= ENERGY_THRESHOLD:
                    interrupt_event.set()
                else:
                    logger.debug(f"[echo] Low-energy frame ({rms:.0f}), skipping.")
                    return

                # ── Speech-to-Text ─────────────────────────────────
                transcript = stt_model.stt((sample_rate, audio_np))

                if not transcript or len(transcript.strip()) < 2:
                    logger.debug("[echo] Empty transcript, skipping.")
                    return

                logger.info(f"[echo] User said: {transcript!r}")
                interrupt_event.clear()

                # Send transcript to the frontend via data channel
                try:
                    handler_ref.send_message_sync(
                        json.dumps({"type": "transcript", "role": "user", "text": transcript})
                    )
                except Exception:
                    pass  # channel may not be ready yet

                # ── LLM streaming ──────────────────────────────────
                llm_stream = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": transcript},
                    ],
                    stream=True,
                    temperature=0.65,
                    max_tokens=150,
                )

                buffer = ""
                ai_response_acc = ""

                for chunk in llm_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        buffer += token
                        ai_response_acc += token

                        # Speak sentence-by-sentence for low latency
                        if any(p in buffer for p in [".", "?", "!", ","]):
                            sentence = buffer.strip()
                            buffer = ""
                            for audio_chunk in tts_model.stream_tts_sync(sentence):
                                if interrupt_event.is_set():
                                    logger.info("[echo] TTS interrupted by user speech.")
                                    return
                                yield audio_chunk

                
                if buffer.strip():
                    for audio_chunk in tts_model.stream_tts_sync(buffer.strip()):
                        if interrupt_event.is_set():
                            return
                        yield audio_chunk

                # Send AI response back to frontend
                try:
                    handler_ref.send_message_sync(
                        json.dumps({"type": "transcript", "role": "assistant", "text": ai_response_acc.strip()})
                    )
                except Exception:
                    pass

            except Exception as exc:
                logger.error(f"[echo] Unhandled error: {exc}")

        # Initialise the parent ReplyOnPause with our closures
        super().__init__(
            fn=echo,
            startup_fn=startup,
            can_interrupt=True,
            output_sample_rate=24000,
            input_sample_rate=48000,
        )

    # Called by FastRTC for every new WebRTC connection
    def copy(self) -> "PerConnectionHandler":
        logger.info("[stream] New connection → spawning isolated handler.")
        return PerConnectionHandler()


# ─────────────────────────────────────────────
# FastRTC Stream
# ─────────────────────────────────────────────
stream = Stream(
    handler=PerConnectionHandler(),
    modality="audio",
    mode="send-receive",
    concurrency_limit=20,   # max simultaneous WebRTC sessions
    time_limit=600,         
)

# ─────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────
app = FastAPI(
    title="AI Voice Assistant",
    description="Concurrent voice AI powered by FastRTC + OpenAI",
    version="1.0.0",
)

# Serve the custom HTML frontend
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

# Health / readiness probe
@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "concurrency_limit": 20})

# Mount FastRTC endpoints:
#   POST /webrtc/offer
#   GET  /websocket/offer   (WS)
#   POST /telephone/incoming
#   WS   /telephone/handler
stream.mount(app)

# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Voice Assistant on http://0.0.0.0:8080")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="warning",   # suppress uvicorn noise; loguru handles app logs
    )
