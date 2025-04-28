import socket

from psocket import PerfectSocket

SRC_IP = "127.0.0.1"
SRC_PORT = 12345

DST_IP = "host.docker.internal"
DST_PORT = 5405


def main():
    src_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    src_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    src_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    src_sock.bind((SRC_IP, SRC_PORT))

    count = 0

    with PerfectSocket() as ps:
        while True:
            data, _ = src_sock.recvfrom(65535)
            count += 1
            print(f"received {count} packets, size: {len(data)} bytes")
            ps.sendto(data, (DST_IP, DST_PORT))


if __name__ == "__main__":
    main()
