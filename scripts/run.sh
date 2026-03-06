#!/bin/bash

echo "Starting Voicebot Deployment..."

# Move to project directory
cd $(dirname "$0")/..

echo "Activating virtual environment..."

. venv/bin/activate

echo "Checking if voicebot already running..."

if lsof -i :8080 > /dev/null
then
    echo "Voicebot already running on port 8080"
    exit 0
fi

echo "Starting Voicebot..."

nohup python src/app.py > app.log 2>&1 &

sleep 3

echo "Voicebot started successfully on port 8080"