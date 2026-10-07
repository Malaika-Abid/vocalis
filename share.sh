#!/bin/bash
set -e

cd "$(dirname "$0")"

# Check if cloudflared exists
if [ ! -f "./cloudflared" ]; then
    echo "Downloading Cloudflare tunnel binary..."
    curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
    chmod +x cloudflared
fi

echo "=========================================================="
echo "   Vocalis 🎙️  Team Sharing Launcher (via Cloudflare)"
echo "=========================================================="
echo " • No ngrok warning screens or interstitials"
echo " • Free, secure HTTPS with valid SSL certificate"
echo " • Microphone works immediately on iPhone, Android & PC"
echo "=========================================================="
echo ""
echo "Starting secure tunnel to http://localhost:8000 ..."
echo "Look for the link ending in '.trycloudflare.com' below:"
echo ""

exec ./cloudflared tunnel --url http://localhost:8000

