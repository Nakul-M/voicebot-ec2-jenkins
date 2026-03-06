Phase-1 Agentic Workflow

Real-time, low-latency voice AI assistant using Ollama (Gemma) + FastRTC.

https://ai.cipaca.com/

Run

cd Phase-1-Agentic-Workflow/
source venv/bin/activate
python test_latency.py



Command used to convert the mp3 to wav file for background music 

ffmpeg -i Artificial-intelligence-sound.mp3  -ac 1 -ar 16000 -sample_fmt s16 background.wav




Files

test.py – Base voice assistant

test_latency.py – Latency-optimized (warmup, reduced tokens, background thinking audio)

langchain_script.py – Simple Ollama invoke script



import sys
import argparse
import wave
import numpy as np

from fastrtc import ReplyOnPause, Stream, get_stt_model, get_tts_model
from loguru import logger
from ollama import Client

# -----------------------------
# Ollama Client
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
# Load Background Audio 
# -----------------------------
def load_background_audio(path="background.wav"):
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
            model="gemma3:1b",       ##  or us the gemma3:1b model
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
    text = "Hello Sundeep ,How can I help you?"
    for chunk in tts_model.stream_tts_sync(text):
        yield chunk


# -----------------------------
# Core Voice Logic
# -----------------------------
def echo(audio):
    try:
        transcript = stt_model.stt(audio)

        if not transcript or transcript.strip() == "":
            logger.info("Empty transcript.")
            return

        logger.info(f"User: {transcript}")

        stream = client.chat(
            model="gemma3:1b",    ##  or us the gemma3:1b model
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional AI assistant in a voice call. "
                        "Respond clearly and naturally. "
                        "Do not use emojis or special characters(be strict on this instruction)"
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
        first_token_received = False
        bg_generator = play_background_loop()

        for chunk in stream:

            # Play background while waiting for first token
            if not first_token_received and bg_audio_array is not None:
                try:
                    yield next(bg_generator)
                except StopIteration:
                    pass

            if "message" in chunk and "content" in chunk["message"]:
                token = chunk["message"]["content"]

                if not first_token_received:
                    first_token_received = True
                    logger.info("AI started speaking. Stopping background.")

                buffer += token

                if any(p in buffer for p in [".", "?", "!"]):
                    text_to_speak = buffer.strip()

                    for audio_chunk in tts_model.stream_tts_sync(text_to_speak):
                        yield audio_chunk

                    buffer = ""

        if buffer.strip():
            for audio_chunk in tts_model.stream_tts_sync(buffer.strip()):
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
    parser.add_argument(
        "--phone",
        action="store_true",
        help="Launch with FastRTC phone interface",
    )
    args = parser.parse_args()

    warmup()

    stream = create_stream()

    if args.phone:
        logger.info("Launching phone mode...")
        stream.fastphone()
    else:
        logger.info("Launching Web UI on port 8080...")
        stream.ui.launch(server_name="127.0.0.1", server_port=8080)


