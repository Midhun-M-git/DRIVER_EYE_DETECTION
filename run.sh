#!/usr/bin/env bash
# Driver Eye Detection System Launcher
set -e

echo "Starting Driver Eye Detection System..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

python3 main.py
