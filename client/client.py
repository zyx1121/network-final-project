import argparse
import time

from psocket import PerfectSocket

DST_IP = "192.168.2.100"
DST_PORT = 5405


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=0.001)
    args = parser.parse_args()

    with PerfectSocket() as ps:
        for i in range(1001):
            data = f"packet {i} sent at {time.time()}".encode("utf-8")
            ps.sendto(data, (DST_IP, DST_PORT))
            time.sleep(args.delay)


if __name__ == "__main__":
    main()
