import socket

from psocket import PerfectSocket

SRC_IP = "localhost"
SRC_PORT = 12345

DST_IP = "192.168.2.100"
DST_PORT = 5405

total_packets = 0
total_size = 0


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    s.bind((SRC_IP, SRC_PORT))

    global total_packets, total_size

    with PerfectSocket() as ps:
        while True:
            data, _ = s.recvfrom(65535)
            total_packets += 1
            total_size += len(data)
            print(f"send {count} packets, size: {len(data)} bytes")
            ps.sendto(data, (DST_IP, DST_PORT))


if __name__ == "__main__":
    try:
        main()
    except:
        print("-------------------------------")
        print("total packets :", total_packets)
        print("total size :", total_size, "bytes")
