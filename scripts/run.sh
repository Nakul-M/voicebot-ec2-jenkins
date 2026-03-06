#!/bin/bash

echo "Starting Voicebot Deployment..."

# Move to project directory
cd $(dirname "$0")/..

# Activate virtual environment
source venv/bin/activate

echo "Starting Ollama server..."

# Start Ollama if not already running
if ! pgrep -x "ollama" > /dev/null
then
    nohup ollama serve > ollama.log 2>&1 &
    sleep 5
fi

echo "Pulling model if not present... "
ollama pull gemma3:1b

echo "Starting Voicebot... kr mazaa"

nohup python src/app.py > app.log 2>&1 &

echo "Voicebot started successfully on port 8080"