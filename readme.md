Phase-1 Agentic Workflow

Real-time, low-latency voice AI assistant using Ollama (Gemma) + FastRTC.



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


