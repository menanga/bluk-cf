#!/bin/bash
# Xvfb startup wrapper for Docker

# Start Xvfb in background
Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 2

# Run the app
python main.py

# Cleanup
kill $XVFB_PID 2>/dev/null || true
