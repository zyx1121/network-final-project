import argparse
import multiprocessing
import os
import queue
import random
import socket
import threading
import time


def worker(host_ip, host_port, dst_ip, dst_port, loss_rate):
    q = queue.Queue(maxsize=10000)

    def receiver(sock):
        while True:
            data, addr = sock.recvfrom(65535)
            if random.random() < loss_rate:
                continue
            try:
                q.put(data, timeout=0.01)
            except queue.Full:
                continue

    def sender(sock):
        while True:
            try:
                data = q.get(timeout=0.01)
                sock.sendto(data, (dst_ip, dst_port))
            except queue.Empty:
                continue

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    if hasattr(socket, "SO_REUSEPORT"):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.bind((host_ip, host_port))

    threading.Thread(target=receiver, args=(s,), daemon=True).start()
    threading.Thread(target=sender, args=(s,), daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-ip", type=str, default="0.0.0.0")
    parser.add_argument("--host-port", type=int, default=5405)
    parser.add_argument("--dst-ip", type=str, default="192.168.2.3")
    parser.add_argument("--dst-port", type=int, default=5405)
    parser.add_argument("--loss-rate", type=float, default=0.1)
    args = parser.parse_args()
    procs = []
    for _ in range(os.cpu_count()):
        p = multiprocessing.Process(
            target=worker,
            args=(
                args.host_ip,
                args.host_port,
                args.dst_ip,
                args.dst_port,
                args.loss_rate,
            ),
        )
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
