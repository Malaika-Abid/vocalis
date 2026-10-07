#!/bin/bash
set -e

# Change to script directory
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found. Creating..."
    python3.10 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

echo "Starting Vocalis Web UI..."
exec .venv/bin/python main.py "$@"

