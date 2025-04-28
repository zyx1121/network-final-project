#!/bin/bash

if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg could not be found"
    echo "auto installing ffmpeg"
    sudo apt-get update && sudo apt-get install -y ffmpeg
    echo "ffmpeg installed"
fi

echo "start receiving"
ffplay -fflags nobuffer -flags low_delay -i udp://0.0.0.0:23456
