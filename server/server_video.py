import socket

from psocket import PerfectSocket

HOST_IP = "0.0.0.0"
HOST_PORT = 5405

FFPLAY_IP = "127.0.0.1"
FFPLAY_PORT = 23456


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)

    count = 0

    with PerfectSocket((HOST_IP, HOST_PORT)) as ps:
        while True:
            data, _ = ps.recvfrom()
            count += 1
            print(f"received {count} packets, size: {len(data)} bytes")
            s.sendto(data, (FFPLAY_IP, FFPLAY_PORT))


if __name__ == "__main__":
    main()
