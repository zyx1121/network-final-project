#!/bin/bash

if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg could not be found"
    echo "auto installing ffmpeg"
    sudo apt-get update && sudo apt-get install -y ffmpeg
    echo "ffmpeg installed"
fi

echo "start streaming"
ffmpeg -re -i video.mp4 -f mpegts udp://127.0.0.1:12345
