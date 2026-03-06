import sys
import argparse

from fastrtc import ReplyOnPause, Stream, get_stt_model, get_tts_model
from loguru import logger
from ollama import Client

# -----------------------------
# Ollama Client (Local Service)
# -----------------------------
client = Client(host="http://127.0.0.1:11434")

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
# Warmup Ollama (Silent Warmup)
# -----------------------------
def warmup():
    try:
        logger.info("Warming up Ollama model silently...")
        client.chat(
            model="gemma3:1b",
            messages=[{"role": "system", "content": "Warmup"}],
            options={
                "num_predict": 1,
                "temperature": 0,
            },
        )
        logger.info("Warmup complete.")
    except Exception as e:
        logger.error(f"Warmup failed: {e}")


# -----------------------------
# Core Voice Logic (Streaming)
# -----------------------------
def echo(audio):
    try:
        transcript = stt_model.stt(audio)

        if not transcript or transcript.strip() == "":
            logger.info("Empty transcript.")
            return

        logger.info(f"User: {transcript}")

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
            options={
                "num_predict": 40,
                "temperature": 0.6,
            },
        )

        buffer = ""

        for chunk in stream:
            if "message" in chunk and "content" in chunk["message"]:
                token = chunk["message"]["content"]
                buffer += token

                if any(p in buffer for p in [".", "?", "!"]):
                    text_to_speak = buffer.strip()
                    logger.info(f"AI (partial): {text_to_speak}")

                    for audio_chunk in tts_model.stream_tts_sync(text_to_speak):
                        yield audio_chunk

                    buffer = ""

        if buffer.strip():
            logger.info(f"AI (final): {buffer.strip()}")
            for audio_chunk in tts_model.stream_tts_sync(buffer.strip()):
                yield audio_chunk

    except Exception as e:
        logger.error(f"Error: {e}")


# -----------------------------
# Create Stream
# -----------------------------
def create_stream():
    return Stream(
        ReplyOnPause(echo),
        modality="audio",
        mode="send-receive",
    )


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Voice Assistant")
    parser.add_argument(
        "--phone",
        action="store_true",
        help="Launch with FastRTC phone interface",
    )
    args = parser.parse_args()

    warmup()  # Silent warmup (no Hello)

    stream = create_stream()

    if args.phone:
        logger.info("Launching phone mode...")
        stream.fastphone()
    else:
        logger.info("Launching Web UI on port 8080...")
        stream.ui.launch(server_name="127.0.0.1", server_port=8080)