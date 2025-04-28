# Communication Network Final Project

## Setup

```bash
docker compose up -d
```

## Server

```bash
docker exec -it server bash
```

```bash
python server.py
```

## Proxy

```bash
docker exec -it proxy bash
```

```bash
python proxy.py
```

## Client

```bash
docker exec -it client bash
```

```bash
python client.py
```

## FFPLAY

```bash
ffmpeg -re -i video.mp4 -f mpegts udp://127.0.0.1:12345
```

```bash
ffplay -fflags nobuffer -flags low_delay -i udp://0.0.0.0:23456
```
