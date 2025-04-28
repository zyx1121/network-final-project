import queue
import socket
import threading
import time

DST_IP = "192.168.2.3"
DST_PORT = 5405

HOST_IP = "0.0.0.0"
HOST_PORT = 5404

LOSS_RATE = 0
DELAY_RATE = 0
DELAY_TIME = 0

q = queue.Queue()


def receiver(sock):
    while True:
        data, addr = sock.recvfrom(65535)
        q.put(data)


def sender(sock):
    while True:
        data = q.get()
        sock.sendto(data, (DST_IP, DST_PORT))


def main():
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c.bind((HOST_IP, HOST_PORT))
    c.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)  # 4MB
    threading.Thread(target=receiver, args=(c,), daemon=True).start()
    threading.Thread(target=sender, args=(c,), daemon=True).start()
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
