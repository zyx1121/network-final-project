import time

from psocket import PerfectSocket

DST_IP = "192.168.2.100"
DST_PORT = 5405
DELAY = 0.001


def main():
    with PerfectSocket() as ps:
        for i in range(1001):
            data = f"packet {i} sent at {time.time()}".encode("utf-8")
            ps.sendto(data, (DST_IP, DST_PORT))
            time.sleep(DELAY)


if __name__ == "__main__":
    main()
