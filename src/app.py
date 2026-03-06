import sys
import argparse
import wave
import numpy as np
import threading

from fastrtc import ReplyOnPause, Stream, get_stt_model, get_tts_model
from loguru import logger
from ollama import Client

# -----------------------------
# Ollama Client
# -----------------------------
client = Client(host="http://172.26.13.25:11434")

# -----------------------------
# Load Models
# -----------------------------
stt_model = get_stt_model()
tts_model = get_tts_model()

# -----------------------------
# Logger Setup
# -----------------------------
logger.remove()
logger.add(sys.stderr, level="INFO")

# -----------------------------
# Global Interrupt Event
# -----------------------------
interrupt_event = threading.Event()

# -----------------------------
# Load Background Audio
# -----------------------------
def load_background_audio(path="../background.wav"):
    try:
        with wave.open(path, "rb") as wf:
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio_array = np.frombuffer(frames, dtype=np.int16)

            logger.info(f"Background loaded: {sample_rate} Hz")
            return sample_rate, audio_array

    except Exception as e:
        logger.error(f"Failed to load background audio: {e}")
        return None, None


bg_sample_rate, bg_audio_array = load_background_audio()


def play_background_loop(chunk_size=2048):
    if bg_audio_array is None:
        return

    while True:
        for i in range(0, len(bg_audio_array), chunk_size):
            chunk = bg_audio_array[i:i + chunk_size]
            yield (bg_sample_rate, chunk)

# -----------------------------
# Warmup Ollama
# -----------------------------
def warmup():
    try:
        logger.info("Warming up Ollama model silently...")
        client.chat(
            model="gemma3:1b",
            messages=[{"role": "system", "content": "Warmup"}],
            options={"num_predict": 1, "temperature": 0},
        )
        logger.info("Warmup complete.")
    except Exception as e:
        logger.error(f"Warmup failed: {e}")

# -----------------------------
# Startup Voice Message
# -----------------------------
def startup():
    text = "Hello Sundeep, how can I help you?"
    for chunk in tts_model.stream_tts_sync(text):
        yield chunk

# -----------------------------
# Core Voice Logic
# -----------------------------
def echo(audio):
    try:
        if audio is None:
            return

        # ---------------------------------------------
        # Normalize audio input
        # ---------------------------------------------
        if isinstance(audio, tuple) and len(audio) == 2:
            sample_rate, audio_array = audio
        else:
            sample_rate = 16000
            audio_array = audio

        if audio_array is None or len(audio_array) == 0:
            return

        audio_np = np.asarray(audio_array, dtype=np.int16)

        # ---------------------------------------------
        # RMS Energy Detection
        # ---------------------------------------------
        rms = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
        logger.info(f"Detected RMS energy: {rms}")

        ENERGY_THRESHOLD = 400

        # ---------------------------------------------
        # If real speech → STOP TTS IMMEDIATELY
        # ---------------------------------------------
        if rms >= ENERGY_THRESHOLD:
            interrupt_event.set()   # STOP CURRENT TTS NOW
        else:
            logger.info("Low-energy noise ignored.")
            return

        # ---------------------------------------------
        # Process STT
        # ---------------------------------------------
        transcript = stt_model.stt((sample_rate, audio_np))

        if not transcript or len(transcript.strip()) < 2:
            logger.info("Empty or short transcript.")
            return

        logger.info(f"User: {transcript}")

        interrupt_event.clear()

        # ---------------------------------------------
        # LLM Streaming
        # ---------------------------------------------
        stream = client.chat(
            model="gemma3:1b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional AI assistant in a voice call. "
                        "Respond clearly and naturally. "
                        "Do not use emojis or special characters."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            stream=True,
            options={"num_predict": 40, "temperature": 0.6},
        )

        buffer = ""
        first_token_received = False

        for chunk in stream:

            if "message" in chunk and "content" in chunk["message"]:
                token = chunk["message"]["content"]

                if not first_token_received:
                    first_token_received = True
                    logger.info("AI started speaking.")

                buffer += token

                if any(p in buffer for p in [".", "?", "!"]):
                    text_to_speak = buffer.strip()
                    buffer = ""

                    for audio_chunk in tts_model.stream_tts_sync(text_to_speak):

                        if interrupt_event.is_set():
                            logger.info("TTS interrupted instantly.")
                            return

                        yield audio_chunk

        if buffer.strip():
            for audio_chunk in tts_model.stream_tts_sync(buffer.strip()):

                if interrupt_event.is_set():
                    logger.info("Final TTS interrupted instantly.")
                    return

                yield audio_chunk

    except Exception as e:
        logger.error(f"Error: {e}")

# -----------------------------
# Create Stream
# -----------------------------
def create_stream():
    return Stream(
        handler=ReplyOnPause(echo, startup_fn=startup),
        modality="audio",
        mode="send-receive",
        ui_args={"title": "Ollama Voice Assistant"},
    )

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice Assistant")
    parser.add_argument("--phone", action="store_true")
    args = parser.parse_args()

    warmup()

    stream = create_stream()

    if args.phone:
        logger.info("Launching phone mode...")
        stream.fastphone()
    else:
        logger.info("Launching Web UI on port 8080...")
        stream.ui.launch(server_name="0.0.0.0", server_port=8080)